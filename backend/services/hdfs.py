from hdfs import InsecureClient
import os

# Assuming HDFS NameNode is accessible via this hostname within the Docker network
HDFS_NAMENODE_URL = os.environ.get("HDFS_NAMENODE_URL", "http://hadoop-namenode:9870")

class HdfsService:
    def __init__(self, url=HDFS_NAMENODE_URL):
        self.client = InsecureClient(url)
        print(f"HDFS client initialized for URL: {url}")

    def list_directory(self, path: str):
        """Lists the contents of a directory in HDFS."""
        try:
            return self.client.list(path)
        except Exception as e:
            print(f"Error listing HDFS directory '{path}': {e}")
            return None

    def write_file(self, hdfs_path: str, data: str, overwrite: bool = False):
        """Writes string data to a file in HDFS."""
        try:
            self.client.write(hdfs_path, data, overwrite=overwrite)
            print(f"Successfully wrote to HDFS file: {hdfs_path}")
            return True
        except Exception as e:
            print(f"Error writing to HDFS file '{hdfs_path}': {e}")
            return False

    def read_file(self, hdfs_path: str):
        """Reads content from a file in HDFS."""
        try:
            with self.client.read(hdfs_path) as reader:
                content = reader.read()
            return content
        except Exception as e:
            print(f"Error reading HDFS file '{hdfs_path}': {e}")
            return None

# You can create a singleton instance for convenience
hdfs_service = HdfsService()
