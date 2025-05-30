from sandbox import sandboxManager


if __name__ == "__main__":
    manager = sandboxManager()
    # 创建沙箱
    sandbox = manager.create_sandbox(image="python:3.12", name="test-sandbox", command="sleep infinity")
    
    # 执行命令(synchronous)
    output = sandbox.exec_command("echo hello world")
    print(output)

    # 执行命令(asynchronous)
    generator = sandbox.exec_command_stream("pip install vllm")
    with output in generator:
        for line in generator:
            print(line)

    # 销毁沙箱
    manager.destroy_sandbox(sandbox)
