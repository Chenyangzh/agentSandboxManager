import sys

from sandbox import sandboxManager


def generate_as_str(generator):
    for output in generator:
        print(output)

def generate_as_terminal(generator):
    for event in generator:
        if "stdout" in event:
            sys.stdout.write(event["stdout"])
            sys.stdout.flush()

if __name__ == "__main__":
    manager = sandboxManager()
    # 创建沙箱
    sandbox = manager.create_sandbox(image="python:3.12", name="test-sandbox", command="sleep infinity")
    
    # 执行命令(synchronous)
    output = sandbox.exec_command("echo hello world")
    print(output)

    # 执行命令(asynchronous)
    generator = sandbox.exec_command_stream("pip install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple")
    generate_as_terminal(generator)    

    # 销毁沙箱
    manager.destroy_sandbox(sandbox)

    print("dbg")
