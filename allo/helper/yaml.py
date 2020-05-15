import yaml


def quick_dict(**args):
    return args


def write_yaml(config_dict, filename):
    with open(filename, 'w') as file:
        documents = yaml.dump(config_dict, file)


def load_yaml(filename):
    with open(filename) as file:
        config_dict = yaml.load(file, Loader=yaml.FullLoader)
    return config_dict

