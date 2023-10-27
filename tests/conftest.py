import ssl
from typing import Iterator

import pytest
from trustme import (
    CA,
    LeafCert,
)


@pytest.fixture
def ca() -> Iterator[CA]:
    """A root CA."""
    yield CA()


@pytest.fixture
def tls_ca_path(ca: CA) -> Iterator[str]:
    """Path for the CA certificate."""
    with ca.cert_pem.tempfile() as ca_cert_pem:
        yield ca_cert_pem


@pytest.fixture
def tls_certificate(ca: CA) -> Iterator[LeafCert]:
    """A leaf certificate."""
    yield ca.issue_cert("localhost", "127.0.0.1", "::1")


@pytest.fixture
def tls_public_key_path(tls_certificate: LeafCert) -> Iterator[str]:
    """Provide a certificate chain PEM file path via fixture."""
    with tls_certificate.private_key_and_cert_chain_pem.tempfile() as cert_pem:
        yield cert_pem


@pytest.fixture
def tls_private_key_path(tls_certificate: LeafCert) -> Iterator[str]:
    """Provide a certificate private key PEM file path via fixture."""
    with tls_certificate.private_key_pem.tempfile() as cert_key_pem:
        yield cert_key_pem


@pytest.fixture
def ssl_context(tls_certificate: LeafCert) -> Iterator[ssl.SSLContext]:
    """SSL context with the test CA."""
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_certificate.configure_cert(ssl_ctx)
    yield ssl_ctx


@pytest.fixture
def ssl_context_server(
    ca: CA, tls_public_key_path: str
) -> Iterator[ssl.SSLContext]:
    """SSL context for server authentication."""
    ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    ca.configure_trust(ssl_ctx)
    yield ssl_ctx
