from kumar_service.hd.setup.install import add_fts_index


def execute():
    print("Adding FULLTEXT Index")
    add_fts_index()
