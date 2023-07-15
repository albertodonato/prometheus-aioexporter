import ssl

import pytest
import trustme


@pytest.fixture
def ca():
    return trustme.CA()


@pytest.fixture
def tls_ca_path(ca):
    with ca.cert_pem.tempfile() as ca_cert_pem:
        yield ca_cert_pem


@pytest.fixture
def tls_certificate(ca):
    return ca.issue_cert("localhost", "127.0.0.1", "::1")


@pytest.fixture
def tls_public_key_path(tls_certificate):
    """Provide a certificate chain PEM file path via fixture."""
    with tls_certificate.private_key_and_cert_chain_pem.tempfile() as cert_pem:
        yield cert_pem


@pytest.fixture
def tls_private_key_path(tls_certificate):
    """Provide a certificate private key PEM file path via fixture."""
    with tls_certificate.private_key_pem.tempfile() as cert_key_pem:
        yield cert_key_pem


@pytest.fixture
def ssl_context(tls_certificate):
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_certificate.configure_cert(ssl_ctx)
    return ssl_ctx


@pytest.fixture
def ssl_context_server(tls_public_key_path, ca):
    ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ca.configure_trust(ssl_ctx)
    return ssl_ctx
