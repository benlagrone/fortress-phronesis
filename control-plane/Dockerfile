FROM debian:12-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     git \
     openssh-client \
     ca-certificates \
     curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Expect repo and SSH keys to be bind-mounted at runtime.
CMD ["/bin/bash"]
