# Security policy

## Supported versions

Only the latest tagged release is supported. This research software is not
approved for real-vehicle or safety-critical use.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities that could expose credentials,
private data, arbitrary code execution or unsafe model deserialization.
Use the repository's private **Security > Advisories > Report a vulnerability**
form. A dedicated security contact will be inserted when the author metadata is
frozen.

Include the affected commit, environment, reproduction steps and impact. Do
not attach sensitive checkpoints or access tokens. The maintainer will
acknowledge a complete report within seven days and coordinate disclosure after
a fix is available.

PyTorch checkpoint loading can execute unsafe pickle payloads. Load only the
published checksummed files from this repository and do not load untrusted
`.pt` files.
