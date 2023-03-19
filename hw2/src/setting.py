def get_hosts():
    command = "h1 h2 h3 h4 h5 h6 h7 h8"
    return command


def get_switches():
    command = "s1 s2 s3 s4 s5 s6 s7"
    return command


def get_ip():
    ip_dict = {
        "h1": "h1ip",
        "h2": "h2ip",
        "h3": "h3ip",
        "h4": "h4ip",
        "h5": "h5ip",
        "h6": "h6ip",
        "h7": "h7ip",
        "h8": "h8ip",
    }
    return ip_dict


def get_mac():
    mac_dict = {
        "h1": "h1mac",
        "h2": "h2mac",
        "h3": "h3mac",
        "h4": "h4mac",
        "h5": "h5mac",
        "h6": "h6mac",
        "h7": "h7mac",
        "h8": "h8mac",
    }
    return mac_dict


def get_links():
    command = (
        "h1,s1 h2,s1 h3,s3 h4,s3 s1,s2 "
        "s2,s3 h5,s4 h6,s4 h7,s6 h8,s6 "
        "s4,s5 s5,s6 s2,s7 s5,s7"
    )
    return command
