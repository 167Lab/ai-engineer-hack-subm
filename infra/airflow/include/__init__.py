"""
Runtime helpers for generated Airflow DAGs.

This package is mounted into Airflow as `include/` so generated templates can
import helpers like `from include.ops.file_io import read_files`.
"""


