# Security and privacy

This is research reference software, not a certified privacy boundary. Input text
can contain personal information even when its JSON schema is valid. Use trusted,
appropriately licensed caches and review their provenance before processing them.

The offline commands make no network requests. The explicit answer command sends
questions, options, and selected document text to a configured model endpoint.
Use a local server for data that cannot leave the machine. Never commit credentials,
restricted dataset files, or generated predictions containing private information.

Report vulnerabilities privately through GitHub's security advisory mechanism when
enabled. Otherwise contact a corresponding author through the paper's institutional
contact details. Do not post working credentials, personal data, or an exploit with
private data in a public issue. Rotate an exposed credential immediately; deleting
it from the current file does not erase repository history.

The current release is the only maintained version. Tests and automated scans
reduce risk but cannot establish that a release is free of every security issue.
