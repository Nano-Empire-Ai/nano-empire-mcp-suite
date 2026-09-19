import os
import subprocess

def deploy_swarm():
    print("========================================")
    print("   NANO EMPIRE: SWARM DEPLOYMENT        ")
    print("========================================")
    
    tools_to_build = [
        {"name": "CryptoPriceOracle", "endpoint": "https://api.coingecko.com/api/v3/simple/price", "price": 0.01},
        {"name": "IPGeoLocator", "endpoint": "http://ip-api.com/json/", "price": 0.01},
        {"name": "PublicJokeGenerator", "endpoint": "https://official-joke-api.appspot.com/random_joke", "price": 0.01}
    ]
    
    for tool in tools_to_build:
        print(f"\n[>] Generating {tool['name']}...")
        out_dir = f"./generated_mcp/{tool['name'].lower()}"
        
        # 1. Generate the tool
        subprocess.run([
            "python", "scripts/generate_mcp_tollbooth.py",
            "--name", tool["name"],
            "--endpoint", tool["endpoint"],
            "--price", str(tool["price"]),
            "--out", out_dir
        ], check=True)
        
    print("\n[>] Swarm generation complete. Handing off to Auto-Deployer...")
    
    # 2. Deploy the whole folder
    subprocess.run([
        "python", "scripts/auto_deploy_mcp.py",
        "--dir", "./generated_mcp",
        "--project", "gen-lang-client-0124637641"
    ])

if __name__ == "__main__":
    deploy_swarm()
