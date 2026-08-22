#!/usr/bin/env python3
"""Run the Pericope payment fixture flow through the browser with Playwright."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request


class E2EFailure(RuntimeError):
    """Raised when the browser E2E contract fails."""


API_LAUNCHER = textwrap.dedent(
    """
    import ast
    import os
    import sys
    import types
    import typing

    sys.path.insert(0, os.getcwd())

    def install_eval_type_backport_stub():
        if 'eval_type_backport' in sys.modules:
            return
        module = types.ModuleType('eval_type_backport')

        def flatten_union(node):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                return flatten_union(node.left) + flatten_union(node.right)
            return [node]

        class UnionTransformer(ast.NodeTransformer):
            def visit_BinOp(self, node):
                node = self.generic_visit(node)
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                    items = [UnionTransformer().visit(item) for item in flatten_union(node)]
                    subscript_slice = items[0] if len(items) == 1 else ast.Tuple(elts=items, ctx=ast.Load())
                    return ast.Subscript(
                        value=ast.Attribute(
                            value=ast.Name(id='typing', ctx=ast.Load()),
                            attr='Union',
                            ctx=ast.Load(),
                        ),
                        slice=subscript_slice,
                        ctx=ast.Load(),
                    )
                return node

            def visit_Name(self, node):
                if node.id == 'None':
                    return ast.Call(
                        func=ast.Name(id='type', ctx=ast.Load()),
                        args=[ast.Constant(None)],
                        keywords=[],
                    )
                return node

        def eval_type_backport(value, globalns=None, localns=None, try_default=False):
            if not isinstance(value, str):
                return value
            tree = ast.parse(value, mode='eval')
            transformed = UnionTransformer().visit(tree)
            ast.fix_missing_locations(transformed)
            namespace = {'typing': typing}
            if globalns:
                namespace.update(globalns)
            if localns:
                namespace.update(localns)
            return eval(compile(transformed, '<eval_type_backport>', 'eval'), namespace, namespace)

        module.eval_type_backport = eval_type_backport
        sys.modules['eval_type_backport'] = module

    def install_mysql_stub():
        if 'mysql.connector' in sys.modules and hasattr(sys.modules['mysql.connector'], 'pooling'):
            return
        mysql_module = types.ModuleType('mysql')
        connector_module = types.ModuleType('mysql.connector')
        pooling_module = types.ModuleType('mysql.connector.pooling')

        class DummyError(Exception):
            pass

        class DummyPool:
            def __init__(self, *args, **kwargs):
                pass

            def get_connection(self):
                raise DummyError('mysql connector is unavailable in browser e2e api harness')

        def connect(*args, **kwargs):
            raise DummyError('mysql connector is unavailable in browser e2e api harness')

        connector_module.Error = DummyError
        connector_module.connect = connect
        connector_module.pooling = pooling_module
        pooling_module.MySQLConnectionPool = DummyPool
        mysql_module.connector = connector_module
        sys.modules['mysql'] = mysql_module
        sys.modules['mysql.connector'] = connector_module
        sys.modules['mysql.connector.pooling'] = pooling_module

    def install_jose_stub():
        if 'jose' in sys.modules:
            return
        jose_module = types.ModuleType('jose')
        jwt_module = types.ModuleType('jose.jwt')
        jwt_module.get_unverified_header = lambda token: {}
        jwt_module.decode = lambda *args, **kwargs: {}
        jose_module.jwt = jwt_module
        sys.modules['jose'] = jose_module
        sys.modules['jose.jwt'] = jwt_module

    def install_llama_index_stub():
        if 'llama_index.llms.ollama' in sys.modules:
            return
        llama_index_module = types.ModuleType('llama_index')
        llms_module = types.ModuleType('llama_index.llms')
        ollama_module = types.ModuleType('llama_index.llms.ollama')

        class DummyOllama:
            def __init__(self, *args, **kwargs):
                pass

            def complete(self, prompt):
                return ''

        ollama_module.Ollama = DummyOllama
        llms_module.ollama = ollama_module
        llama_index_module.llms = llms_module
        sys.modules['llama_index'] = llama_index_module
        sys.modules['llama_index.llms'] = llms_module
        sys.modules['llama_index.llms.ollama'] = ollama_module

    install_eval_type_backport_stub()
    install_jose_stub()
    install_mysql_stub()
    install_llama_index_stub()

    import uvicorn
    import main

    uvicorn.run(main.app, host='127.0.0.1', port=int(os.environ['PERICOPE_PAYMENT_API_PORT']), log_level='warning')
    """
)


def wait_for_url(url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except urllib.error.HTTPError as exc:
            if 200 <= exc.code < 500:
                return
            last_error = exc
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    raise E2EFailure(f"Timed out waiting for {url}: {last_error!r}")


def run_command(cmd: list[str], *, cwd: Path, env: dict[str, str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise E2EFailure(
            f"{label} failed with exit {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def terminate_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Pericope payment browser E2E harness.")
    parser.add_argument(
        "--service-dir",
        default=str(Path(__file__).resolve().parents[2] / "pericopeai.com" / "AugustineService"),
    )
    parser.add_argument(
        "--frontend-dir",
        default=str(Path(__file__).resolve().parents[2] / "pericopeai.com" / "AugustineFE"),
    )
    parser.add_argument("--python-bin", default=os.getenv("PERICOPE_PYTHON_BIN", sys.executable))
    parser.add_argument("--npm-bin", default=os.getenv("PERICOPE_NPM_BIN", "npm"))
    parser.add_argument(
        "--pwcli",
        default=os.getenv(
            "PWCLI",
            str(Path.home() / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"),
        ),
    )
    parser.add_argument("--api-port", type=int, default=18081)
    parser.add_argument("--frontend-port", type=int, default=13082)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    service_dir = Path(args.service_dir).resolve()
    frontend_dir = Path(args.frontend_dir).resolve()
    pwcli = Path(args.pwcli).resolve()
    output_dir = Path(__file__).resolve().parents[1] / "output" / "playwright" / "pericope-payment-e2e"
    output_dir.mkdir(parents=True, exist_ok=True)
    api_log = output_dir / "api.log"
    fe_log = output_dir / "frontend.log"
    launcher_path = output_dir / "payment_fixture_api_launcher.py"
    launcher_path.write_text(API_LAUNCHER, encoding="utf-8")

    if not shutil.which("npx"):
        raise E2EFailure("npx is required for Playwright CLI")
    if not pwcli.is_file():
        raise E2EFailure(f"Playwright wrapper script not found: {pwcli}")

    api_env = os.environ.copy()
    api_env.update(
        {
            "ENVIRONMENT": "dev",
            "AUTH_ENFORCED": "false",
            "DEV_FAKE_AUTH": "true",
            "PERICOPE_BILLING_PROVIDER": "fixture",
            "PERICOPE_PAYMENT_API_PORT": str(args.api_port),
        }
    )
    frontend_env = os.environ.copy()
    frontend_env.update(
        {
            "BROWSER": "none",
            "PORT": str(args.frontend_port),
            "REACT_APP_API_BASE_URL": f"http://127.0.0.1:{args.api_port}/api",
            "REACT_APP_DISABLE_AUTH": "true",
            "REACT_APP_DEV_AUTH_SUB": "dummy-paid-reader",
            "REACT_APP_DEV_AUTH_EMAIL": "dummy-paid-reader+test@pericopeai.com",
            "REACT_APP_DEV_AUTH_GIVEN_NAME": "Dummy",
            "REACT_APP_DEV_AUTH_FAMILY_NAME": "Reader",
            "REACT_APP_DEV_AUTH_NAME": "Dummy Reader",
            "REACT_APP_DEV_AUTH_ROLES": "default-roles-pericope",
        }
    )
    playwright_env = os.environ.copy()
    playwright_env["PLAYWRIGHT_CLI_SESSION"] = "pericope-payment-e2e"

    api_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None
    try:
        api_log_handle = api_log.open("w", encoding="utf-8")
        frontend_log_handle = fe_log.open("w", encoding="utf-8")
        api_process = subprocess.Popen(
            [args.python_bin, str(launcher_path)],
            cwd=str(service_dir),
            env=api_env,
            stdout=api_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        frontend_process = subprocess.Popen(
            [args.npm_bin, "start"],
            cwd=str(frontend_dir),
            env=frontend_env,
            stdout=frontend_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        wait_for_url(f"http://127.0.0.1:{args.api_port}/api/healthz", timeout_seconds=args.timeout)
        wait_for_url(f"http://127.0.0.1:{args.frontend_port}/pricing", timeout_seconds=args.timeout)

        api_base_url = f"http://127.0.0.1:{args.api_port}/api/v1"
        pricing_url = f"http://127.0.0.1:{args.frontend_port}/pricing"
        profile_url = f"http://127.0.0.1:{args.frontend_port}/user/profile/home"

        run_command(
            [str(pwcli), "open", "about:blank"],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright open browser",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                textwrap.dedent(
                    f"""
                    async page => {{
                      page.__pericopePaymentConsoleErrors = [];
                      page.on('console', msg => {{
                        if (msg.type() === 'error') {{
                          page.__pericopePaymentConsoleErrors.push(msg.text());
                        }}
                      }});
                      page.on('pageerror', err => {{
                        page.__pericopePaymentConsoleErrors.push('pageerror: ' + err.message);
                      }});
                      const jsonRoute = (route, body, status = 200) => route.fulfill({{
                        status,
                        contentType: 'application/json',
                        body: JSON.stringify(body),
                        headers: {{ 'Access-Control-Allow-Origin': '*' }},
                      }});
                      await page.route('{api_base_url}/billing/**', route => route.continue());
                      await page.route('{api_base_url}/user/profile/sync', route => jsonRoute(route, {{
                        user_id: 'dummy-paid-reader',
                        first_name: 'Dummy',
                        last_name: 'Reader',
                        email: 'dummy-paid-reader+test@pericopeai.com',
                        has_paid_access: false,
                        subscription_tier: null,
                        subscription_tier_label: null,
                      }}));
                      await page.route('{api_base_url}/user/preferences/authors', route => jsonRoute(route, {{
                        favorite_authors: [],
                        default_author_slug: null,
                        default_author_unavailable_slug: null,
                        updated_at: null,
                      }}));
                      await page.route('{api_base_url}/authors', route => jsonRoute(route, []));
                      await page.route('{api_base_url}/authors/browse', route => jsonRoute(route, {{ items: [], count: 0 }}));
                      await page.route('{api_base_url}/authors/augustine/profile', route => jsonRoute(route, {{
                        slug: 'augustine',
                        name: 'Augustine',
                        biography: {{ summary: 'Fixture author profile for payment E2E.' }},
                        works: [],
                      }}));
                      await page.route('{api_base_url}/crossrefs/**', route => jsonRoute(route, {{ items: [], count: 0 }}));
                      await page.route('{api_base_url}/memory/**', route => jsonRoute(route, {{ items: [], count: 0 }}));
                      await page.route('{api_base_url}/proverbs/content', route => jsonRoute(route, {{
                        author: {{ slug: 'solomon', name: 'Solomon' }},
                        headline: 'Ask Proverbs',
                        description: 'Fixture Proverbs content.',
                        examples: [],
                        anchors: [],
                        source: {{ owned_by: 'pericope', clock_dependency: false }},
                      }}));
                      await page.goto('{pricing_url}', {{ waitUntil: 'networkidle' }});
                      await page.getByRole('heading', {{ name: 'Pricing & Access' }}).waitFor();
                      await page.getByText('No paid subscription on file').waitFor();
                    }}
                    """
                ),
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright wait pricing heading",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                "async page => { await page.screenshot({ path: 'pricing-unpaid.png', fullPage: true }); await page.getByRole('button', { name: 'Start Reader' }).click(); await page.waitForURL(/\\/billing\\/success/); await page.getByRole('heading', { name: 'Billing Success' }).waitFor(); await page.getByText('Checkout created; payment not yet completed').waitFor(); await page.screenshot({ path: 'billing-success-pending.png', fullPage: true }); }",
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright start reader checkout",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                "async page => { await page.getByRole('button', { name: 'Complete Dummy Payment' }).click(); await page.getByText('Payment captured; runtime access still waiting on role sync').waitFor(); await page.screenshot({ path: 'billing-success-completed.png', fullPage: true }); }",
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright complete dummy payment",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                "async page => { await page.getByRole('button', { name: 'Create Customer Portal Link' }).click(); await page.getByRole('link', { name: 'Open Portal' }).waitFor(); }",
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright create portal",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                f"async page => {{ await page.evaluate(() => window.localStorage.setItem('pericope:devAuthRoles', 'reader')); await page.goto('{profile_url}'); await page.waitForLoadState('networkidle'); await page.getByText('Billing tier: Reader').waitFor(); await page.getByText('Payment and paid runtime access are active').waitFor(); await page.screenshot({{ path: 'profile-paid-active.png', fullPage: true }}); }}",
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright verify paid profile state",
        )
        run_command(
            [
                str(pwcli),
                "run-code",
                "async page => { const errors = page.__pericopePaymentConsoleErrors || []; if (errors.length) throw new Error('Browser console errors: ' + errors.join(' | ')); return { consoleErrors: errors }; }",
            ],
            cwd=output_dir,
            env=playwright_env,
            label="Playwright assert clean browser console",
        )
        print(
            f"Browser E2E passed. Artifacts: {output_dir}\n"
            f"API log: {api_log}\nFrontend log: {fe_log}"
        )
        return 0
    except E2EFailure as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        terminate_process(frontend_process)
        terminate_process(api_process)


if __name__ == "__main__":
    raise SystemExit(main())
