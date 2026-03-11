import docker
import os
import time

class DockerRunner:
    def __init__(self, image_name="mini-sh-sandbox"):
        self.client = docker.from_env()
        self.image_name = image_name
        self.workspace_dir = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
        
        try:
            self.client.images.get(self.image_name)
        except docker.errors.ImageNotFound:
            print(f"Image {self.image_name} not found. Please build it first using:")
            print(f"docker build -t {self.image_name} -f Dockerfile.sandbox .")
            raise

    def run_command(self, command: str, timeout: int = 30) -> dict:
        print(f"Running in sandbox: {command}")
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        container = None
        try:
            container = self.client.containers.run(
                self.image_name,
                command=command,
                volumes={self.workspace_dir: {'bind': '/workspace', 'mode': 'rw'}},
                working_dir="/workspace",
                detach=True,
                network_disabled=True, # Security: No internet access for untrusted code
                mem_limit='512m',      # Resource Limit: Protect host RAM for LLM
                cpuset_cpus='0',       # Resource Limit: Pin to single core if needed
                pids_limit=50,         # Security: Prevent fork bombs
            )
            
            start_time = time.time()
            exit_code = -1
            
            # Wait loop with timeout
            while time.time() - start_time < timeout:
                container.reload()
                if container.status == 'exited':
                    result = container.wait()
                    exit_code = result['StatusCode']
                    break
                time.sleep(1)
            else:
                # Timeout occurred
                container.stop()
                return {"exit_code": 124, "output": f"Error: Command timed out after {timeout} seconds", "error": "timeout"}
            
            logs = container.logs().decode("utf-8")
            
            return {
                "exit_code": exit_code,
                "output": logs
            }
            
        except Exception as e:
            return {"exit_code": -1, "output": str(e), "error": str(e)}
        finally:
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass

if __name__ == "__main__":
    runner = DockerRunner()
    res = runner.run_command("python -c \"print('Hello from Docker')\"")
    print(res)
