import os
import io
import logging
import zipfile
import requests

class Client:
    """	
    A generic document downloader class.
    """	
    def __init__(self, download_dir, log_dir, proxies=None):
        """
        Initializes the downloader with directories for downloads and logs.
        
        Parameters
        ----------
        download_dir : str
            Directory where downloaded files will be saved.
        log_dir : str
            Directory where log files will be saved.
        """
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.proxies = proxies
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ensure_directories()
        # Set up logging to file and console if not already set
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.log_dir, 'client.log'), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger.info('Client initialized with download_dir=%s, log_dir=%s', self.download_dir, self.log_dir)

    def _ensure_directories(self):
        """
        Ensure that the download and log directories exist.
        """
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            self.logger.info('Created download directory: %s', self.download_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            self.logger.info('Created log directory: %s', self.log_dir)
    
    def handle_response(self, response, filename):
        """
        Handle a server response by saving or extracting its content.

        Parameters
        ----------
        response : requests.Response
            The HTTP response object.
        folder_path : str
            Directory where the file will be saved.
        cid : str
            CELLAR ID of the document.

        Returns
        -------
        str or None
            Path to the saved file or None if the response couldn't be processed.
        """
        content_type = response.headers.get('Content-Type', '')
        target_path = os.path.join(self.download_dir, filename)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        if 'zip' in content_type:
            self.logger.info('ZIP file detected in response for %s', filename)
            self.extract_zip(response, target_path)
            self.logger.info(f"ZIP file extracted: {target_path}")
            return target_path
        else:
            extension = self.get_extension_from_content_type(content_type)
            if not extension:
                self.logger.warning(f"Unknown content type for ID {filename}: {content_type}")
                return None

            file_path = f"{target_path}.{extension}"
            file_path = os.path.normpath(file_path)
            try:
                with open(file_path, mode='wb+') as f:
                    f.write(response.content)
                self.logger.info(f"File saved: {file_path}")
                return file_path
            except Exception as e:
                self.logger.error(f"Failed to save file {file_path}: {e}")
                return None

    def get_extension_from_content_type(self, content_type):
        """
        Map Content-Type to a file extension.
        
        Parameters
        ----------
        content_type : str
            The Content-Type header from the server response.
        
        Returns
        -------
        str or None
            File extension corresponding to the Content-Type
        """
        content_type_mapping = {
            'text/html': 'html',
            'application/json': 'json',
            'application/xml': 'xml',
            'text/plain': 'txt',
            'application/zip': 'zip',
            'text/xml': 'xml',
            'application/xhtml+xml': 'xhtml',
        }
        for ext, mapped_ext in content_type_mapping.items():
            if ext in content_type:
                return mapped_ext
        self.logger.warning(f"No extension mapping found for content type: {content_type}")
        return None

    # Function to download a zip file and extract it
    def extract_zip(self, response, folder_path):
        """
        Extracts the content of a zip file.
        
        Parameters
        ----------
        response : requests.Response
            The HTTP response object.
        folder_path : str
            Directory where the zip file will be extracted.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(folder_path)
            self.logger.info(f"Extracted ZIP to {folder_path}")
        except Exception as e:
            self.logger.error(f"Failed to extract ZIP file to {folder_path}: {e}")

