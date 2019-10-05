import os

def install_nextgen_data_to_db(download_file = "new_nextgen_chains_mouse_A.tsv", download_from = "dropbox"):
    """

    Function installs next-gen files

    Parameters
    ----------
    download_file : string
        "new_nextgen_chains_mouse_A.tsv"

    Returns
    -------
    installs to tcrdist/db/alphabeta_db.tsv_files/*

    """
    if not isinstance(download_from, str):
        raise TypeError("the < download_from > arg must be a string")
    if download_from not in ["dropbox"]:
        raise KeyError("the < download_from > arg passed to install_blast_to_externals \
        must be one of the following: dropbox")

    if download_from is "dropbox":
        address = { "new_nextgen_chains_mouse_A.tsv" : 'https://www.dropbox.com/s/pkpr6p97eworn3q/new_nextgen_chains_mouse_A.tsv?dl=1',
                    "new_nextgen_chains_mouse_B.tsv" : 'https://www.dropbox.com/s/sxgvrj25mnzr20s/new_nextgen_chains_mouse_B.tsv?dl=1',
                    "new_nextgen_chains_human_A.tsv" : 'https://www.dropbox.com/s/41w8yl38nr4ey32/new_nextgen_chains_human_A.tsv?dl=1',
                    "new_nextgen_chains_human_B.tsv" : 'https://www.dropbox.com/s/8ysciqrcywdsryp/new_nextgen_chains_human_B.tsv?dl=1'}
        if download_file not in address.keys():
            raise ValueError("download_file must be in {}".format(" ".join(map(str,address.keys))))
    # Where the file is to be installed
    path_file = os.path.realpath(__file__)
    path = os.path.dirname(path_file)
    install_path = os.path.join(path, "db", "alphabeta_db.tsv_files", download_file)

    def generate_curl(filename, download_link):
        return('curl -o {} {} -L'.format(filename, download_link))

    curl_url_cmd = generate_curl(install_path, address[download_file])
    print("RUNNING: {}\n".format(curl_url_cmd) )
    os.system(curl_url_cmd)
    return(curl_url_cmd)
