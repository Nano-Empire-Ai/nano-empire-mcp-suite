import os
import subprocess
import argparse
import json

def auto_deploy(base_dir: str, project_id: str, region: str = "us-central1"):
    print(f"========================================")
    print(f"   NANO EMPIRE AUTO-DEPLOYER (MCP)      ")
    print(f"========================================")

    if not os.path.exists(base_dir):
        print(f"[ERROR] Directory {base_dir} not found.")
        return

    # Find all subdirectories in base_dir
    mcp_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    if not mcp_dirs:
        print(f"[INFO] No MCP projects found in {base_dir}")
        return

    for mcp_name in mcp_dirs:
        target_path = os.path.join(base_dir, mcp_name)
        # Format service name (lowercase, hyphens only, max 49 chars)
        service_name = f"nano-mcp-{mcp_name.lower().replace('_', '-')}"[:49]
        
        print(f"\n[>] Deploying {mcp_name} to Cloud Run as '{service_name}'...")
        
        # Ensure .gcloudignore exists to speed up upload
        gcloudignore_path = os.path.join(target_path, ".gcloudignore")
        if not os.path.exists(gcloudignore_path):
            with open(gcloudignore_path, "w") as f:
                f.write(".git\n.venv\n__pycache__\n*.pyc\n")

        # Construct gcloud command
        cmd = [
            "gcloud.cmd", "run", "deploy", service_name,
            "--source", ".",
            "--project", project_id,
            "--region", region,
            "--allow-unauthenticated",
            "--format=json"
        ]

        try:
            # Run the deployment
            result = subprocess.run(
                cmd,
                cwd=target_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output to get the URL
            deploy_info = json.loads(result.stdout)
            service_url = deploy_info.get("status", {}).get("url")
            
            print(f"[+] SUCCESS! {mcp_name} is live at: {service_url}")
            
            # Generate the Smithery Registry JSON
            generate_registry_payload(mcp_name, service_url)
            
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to deploy {mcp_name}.")
            print(e.stderr)

def generate_registry_payload(name: str, url: str):
    payload = {
        "name": f"nano-empire-{name}",
        "version": "1.0.0",
        "description": f"Nano Empire AI x402 Micropayment Tollbooth for {name}.",
        "transport": "sse",
        "endpoint": f"{url}/sse",
        "author": "Nano Empire AI",
        "license": "MIT",
        "mcpServers": {
            f"nano-{name}": {
                "command": "python",
                "args": ["server.py"]
            }
        }
    }
    
    out_dir = os.path.join("artifacts", "registry")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"registry_{name}.json")
    
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"[*] Generated Smithery payload at: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-Deploy Generated MCPs to Cloud Run")
    parser.add_argument("--dir", default="./generated_mcp", help="Directory containing generated MCPs")
    parser.add_argument("--project", default="gen-lang-client-0124637641", help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    
    args = parser.parse_args()
    auto_deploy(args.dir, args.project, args.region)
