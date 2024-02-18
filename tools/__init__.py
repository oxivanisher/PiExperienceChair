import yaml


def read_config(file_path):
    try:
        with open(file_path, 'r') as file:
            config_data = yaml.safe_load(file)
        return config_data
    except FileNotFoundError:
        print(f"Config file '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error reading config file '{file_path}': {e}")
        return None
