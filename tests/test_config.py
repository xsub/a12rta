import pytest
from pydantic import ValidationError
import sys
import os

# Ensure the root directory is in sys.path to import a12rta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from a12rta import HostConfig

def test_host_config_valid_minimal():
    config = HostConfig(
        host="example.com",
        log_files=["/var/log/syslog"]
    )
    assert config.host == "example.com"
    assert config.user is None
    assert config.is_localhost is False
    assert config.log_files == ["/var/log/syslog"]
    assert config.output_format == "compact"
    assert config.buffer_lines == 10

def test_host_config_log_file_string_to_list():
    # Should convert a single string to a list of strings via the validator
    config = HostConfig(
        host="example.com",
        log_files="/var/log/single.log"
    )
    assert isinstance(config.log_files, list)
    assert config.log_files == ["/var/log/single.log"]

def test_host_config_missing_required_fields():
    with pytest.raises(ValidationError):
        HostConfig(user="admin")  # Missing 'host' and 'log_files'

def test_host_config_formats():
    config = HostConfig(
        host="localhost",
        log_files=["a.log"],
        output_format="json"
    )
    assert config.output_format == "json"
