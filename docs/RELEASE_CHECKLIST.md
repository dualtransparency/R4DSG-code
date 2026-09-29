# Release checklist

- [ ] Build and test a clean checkout and installed wheel, not only an editable tree.
- [ ] Run schema, temporal association, retrieval isolation, and mock endpoint tests.
- [ ] Verify README offline commands on the current release.
- [ ] Review all tracked files and source/wheel archive contents.
- [ ] Scan staged files and complete Git history for credentials and private data.
- [ ] Confirm no dataset media, QA, prediction logs, local configs, or model weights.
- [ ] Confirm author/citation metadata and third-party licensing scope.
- [ ] Record actual validation and any untested model or dataset-dependent steps.
- [ ] Review reproduction caveats; do not attach unverified paper-score claims.
- [ ] Create a new repository rather than copying an experimental Git history.
- [ ] Enable private vulnerability reporting when repository settings permit it.
- [ ] Confirm remote owner, visibility, description, homepage, topics, and license.

This checklist applies to each release. A passed software test is not a guarantee
about data provenance, all possible vulnerabilities, or benchmark accuracy.
