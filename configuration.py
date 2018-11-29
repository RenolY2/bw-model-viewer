import configparser


def read_config():
    cfg = configparser.ConfigParser()
    with open("bwviewer.ini", "r") as f:
        cfg.read_file(f)
    print("config file loaded")
    return cfg


def make_default_config():
    cfg = configparser.ConfigParser()

    cfg["default paths"] = {
        "resourceFiles": "",
        "exportedModels": ""
    }

    with open("bwviewer.ini", "w") as f:
        cfg.write(f)

    return cfg


def save_cfg(cfg):
    with open("bwviewer.ini", "w") as f:
        cfg.write(f)