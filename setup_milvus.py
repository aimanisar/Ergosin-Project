#!/usr/bin/env python3
"""
Milvus Setup Script for Competitive Intelligence Dashboard.

This script helps set up Milvus for the application.
It provides options to install and start Milvus using Docker or pip.
"""

import subprocess
import sys
import time
import requests
from pymilvus import connections

def check_milvus_running():
    """Check if Milvus is already running."""
    try:
        connections.connect(alias="test", host="localhost", port="19530")
        connections.disconnect("test")
        return True
    except:
        return False

def install_milvus_docker():
    """Install and start Milvus using Docker."""
    print("🐳 Setting up Milvus with Docker...")
    
    try:
        # Check if Docker is installed
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker is installed")
        
        # Check if Milvus container is already running
        result = subprocess.run(["docker", "ps", "--filter", "name=milvus-standalone", "--format", "{{.Names}}"], 
                              capture_output=True, text=True)
        
        if "milvus-standalone" in result.stdout:
            print("✅ Milvus container is already running")
            return True
        
        # Start Milvus container
        print("🚀 Starting Milvus container...")
        subprocess.run([
            "docker", "run", "-d", "--name", "milvus-standalone",
            "-p", "19530:19530", "-p", "9091:9091",
            "milvusdb/milvus:latest"
        ], check=True)
        
        print("⏳ Waiting for Milvus to start...")
        time.sleep(10)
        
        # Test connection
        if check_milvus_running():
            print("✅ Milvus is running successfully!")
            return True
        else:
            print("❌ Milvus failed to start properly")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error with Docker: {e}")
        return False
    except FileNotFoundError:
        print("❌ Docker is not installed. Please install Docker first.")
        return False

def install_milvus_pip():
    """Install Milvus using pip (standalone mode)."""
    print("📦 Installing Milvus using pip...")
    
    try:
        # Install pymilvus
        subprocess.run([sys.executable, "-m", "pip", "install", "pymilvus>=2.3.0"], check=True)
        print("✅ pymilvus installed successfully")
        
        print("ℹ️  Note: For production use, consider using Milvus with Docker for better performance.")
        print("ℹ️  This pip installation provides basic functionality for development.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing pymilvus: {e}")
        return False

def main():
    """Main setup function."""
    print("🔧 Milvus Setup for Competitive Intelligence Dashboard")
    print("=" * 60)
    
    # Check if Milvus is already running
    if check_milvus_running():
        print("✅ Milvus is already running on localhost:19530")
        print("🎉 You're all set! You can now run your application.")
        return
    
    print("Milvus is not running. Choose an installation method:")
    print("1. Docker (Recommended for production)")
    print("2. Pip (Basic installation for development)")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            if install_milvus_docker():
                print("\n🎉 Milvus setup complete!")
                print("You can now run your application with: streamlit run main.py")
            break
        elif choice == "2":
            if install_milvus_pip():
                print("\n🎉 Milvus setup complete!")
                print("You can now run your application with: streamlit run main.py")
            break
        elif choice == "3":
            print("👋 Setup cancelled.")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
