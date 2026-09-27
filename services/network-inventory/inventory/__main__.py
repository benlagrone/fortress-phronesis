import uvicorn
uvicorn.run('inventory.app:create_app',factory=True,host='0.0.0.0',port=18160,access_log=False)
