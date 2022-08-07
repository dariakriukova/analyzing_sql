import logging
import sys

logger = logging.getLogger()
file_handler = logging.FileHandler("logfile.log")
stream_handler = logging.StreamHandler(sys.stdout)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
stream_formatter = logging.Formatter('%(levelname)s: %(message)s')
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

logger_plt = logging.getLogger('matplotlib')
logger_plt.setLevel(logging.INFO)
