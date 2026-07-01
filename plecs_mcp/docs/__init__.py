"""Offline PLECS documentation knowledge base.

The corpus is extracted from the LOCAL PLECS help (`plecshelp.qch`, a Qt Help
SQLite DB) so it matches the installed version exactly. The extracted text is
Plexim copyright and is NOT committed to git — only this code is. Build the index
locally with `python -m plecs_mcp.docs.extract <plecshelp.qch> <out_dir>`.
"""
