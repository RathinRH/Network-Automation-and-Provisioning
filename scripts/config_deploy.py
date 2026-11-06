"""
Configuration Deployment Script
Deploy configurations to network devices from templates or files
"""

import logging
import os
import sys

# Allow this script to be run from the project root or from scripts/
sys.path.insert(0, os.path.dirname(__file__))

from device_manager import DeviceManager, load_devices_from_yaml
from jinja2 import Template, Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class ConfigDeploy:
    """Handles configuration deployment to network devices"""
    
    def __init__(self, template_dir='config/templates'):
        """
        Initialize deployment manager
        
        Args:
            template_dir (str): Directory containing configuration templates
        """
        self.template_dir = template_dir
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    def deploy_commands(self, device_config, commands):
        """
        Deploy list of commands to a device
        
        Args:
            device_config (dict): Device configuration
            commands (list): List of configuration commands
            
        Returns:
            bool: True if deployment successful
        """
        device_manager = DeviceManager(device_config)
        
        if not device_manager.connect():
            return False
        
        try:
            # Send configuration
            output = device_manager.send_config(commands)
            
            if output:
                logger.info(f"Configuration deployed to {device_config['host']}")
                
                # Save configuration
                device_manager.save_config()
                return True
            else:
                logger.error(f"Failed to deploy to {device_config['host']}")
                return False
                
        except Exception as e:
            logger.error(f"Deployment failed for {device_config['host']}: {str(e)}")
            return False
        finally:
            device_manager.disconnect()
    
    def deploy_from_template(self, device_config, template_name, variables):
        """
        Deploy configuration from Jinja2 template
        
        Args:
            device_config (dict): Device configuration
            template_name (str): Template filename
            variables (dict): Variables to render template
            
        Returns:
            bool: True if deployment successful
        """
        try:
            # Load and render template
            template = self.jinja_env.get_template(template_name)
            config_text = template.render(**variables)
            
            # Split into commands
            commands = [line.strip() for line in config_text.split('\n') 
                       if line.strip() and not line.strip().startswith('#')]
            
            logger.info(f"Rendered template {template_name} with {len(commands)} commands")
            
            # Deploy commands
            return self.deploy_commands(device_config, commands)
            
        except Exception as e:
            logger.error(f"Template deployment failed: {str(e)}")
            return False
    
    def deploy_from_file(self, device_config, config_file):
        """
        Deploy configuration from file
        
        Args:
            device_config (dict): Device configuration
            config_file (str): Path to configuration file
            
        Returns:
            bool: True if deployment successful
        """
        try:
            with open(config_file, 'r') as f:
                config_text = f.read()
            
            commands = [line.strip() for line in config_text.split('\n') 
                       if line.strip() and not line.strip().startswith('#')]
            
            return self.deploy_commands(device_config, commands)
            
        except Exception as e:
            logger.error(f"File deployment failed: {str(e)}")
            return False
    
    def rollback_config(self, device_config, backup_file):
        """
        Rollback to a previous configuration backup
        
        Args:
            device_config (dict): Device configuration
            backup_file (str): Path to backup configuration file
            
        Returns:
            bool: True if rollback successful
        """
        logger.warning(f"Rolling back {device_config['host']} to {backup_file}")
        return self.deploy_from_file(device_config, backup_file)


def main():
    """Main function to run deployment script"""
    import argparse
    import logging.handlers
    from pathlib import Path

    # Activate logging when this script is run directly
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                log_dir / "network_automation.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
        ],
    )

    parser = argparse.ArgumentParser(description='Deploy configurations to network devices')
    parser.add_argument('--devices', default='config/devices.yaml',
                       help='Path to devices YAML file')
    parser.add_argument('--commands', nargs='+',
                       help='Commands to deploy')
    parser.add_argument('--file',
                       help='Configuration file to deploy')
    parser.add_argument('--template',
                       help='Template name to use')
    parser.add_argument('--vars',
                       help='Variables for template (JSON format)')
    parser.add_argument('--host',
                       help='Deploy to specific host only')
    
    args = parser.parse_args()
    
    # Load devices
    devices = load_devices_from_yaml(args.devices)
    
    if args.host:
        devices = [d for d in devices if d.get('host') == args.host]
    
    if not devices:
        logger.error("No devices found")
        return
    
    # Create deployment manager
    deploy_manager = ConfigDeploy()
    
    logger.info("=" * 50)
    logger.info("Starting deployment")
    logger.info("=" * 50)
    
    # Deploy to each device
    for device in devices:
        hostname = device.get('host', 'unknown')
        logger.info(f"Deploying to {hostname}")
        
        if args.commands:
            success = deploy_manager.deploy_commands(device, args.commands)
        elif args.file:
            success = deploy_manager.deploy_from_file(device, args.file)
        elif args.template:
            import json
            variables = json.loads(args.vars) if args.vars else {}
            success = deploy_manager.deploy_from_template(device, args.template, variables)
        else:
            logger.error("No deployment method specified (--commands, --file, or --template)")
            return
        
        logger.info(f"{hostname}: {'SUCCESS' if success else 'FAILED'}")


if __name__ == '__main__':
    main()
