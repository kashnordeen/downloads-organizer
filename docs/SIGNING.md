# Code signing policy

## Current status

Windows v0.2.0 preview downloads are unsigned. SignPath Foundation approval,
account configuration, and signing integration are pending. This document does
not claim sponsorship, certification, or that any existing download is signed.
macOS Developer ID signing and notarization are separate requirements.

## Responsibilities

[Keshav Karn (@kashnordeen)](https://github.com/kashnordeen) maintains the
repository, reviews contributions, and approves releases for signing. New
contributors' changes must be reviewed before inclusion in a signed release.
GitHub and SignPath multi-factor authentication are prerequisites for everyone
with signing responsibilities. The maintainer confirmed GitHub MFA is enabled
on 2026-10-02; SignPath MFA must be enabled during account setup.

## Rules for future signed releases

- Sign only project-owned release artifacts from this repository, built on
  GitHub-hosted runners after the existing tests, audits, and bundle checks pass.
- Require the maintainer's manual approval for every signing request. Pull
  requests, forks, and arbitrary uploaded binaries must not trigger signing.
- Keep submission credentials in GitHub Secrets with limited signing permissions.
- Include upstream dependency binaries under their own licenses; do not re-sign
  them under the project's certificate. Retain source and license notices.
- Verify returned Authenticode signatures, signer identity, and timestamps before
  publication. Generate checksums from the final signed packages and label them
  accurately. A failed signing request must never produce a release labeled signed.

## Privacy

The desktop app processes files locally and does not send file contents, paths,
or usage telemetry to a server. Startup registration is optional. Signing would
send release binaries and GitHub build metadata to SignPath, not users' downloads.
See [SignPath's privacy policy](https://about.signpath.io/privacy-policy).

## Activation checklist

1. Confirm MFA and submit the project for [Foundation review](https://signpath.org/apply.html).
2. After acceptance, publish the provider attribution required by the
   [Foundation's terms](https://signpath.org/terms.html), and configure the real
   organization, project, artifact configuration, approver, and signing policy.
3. Add product/version metadata to the Windows executable. Establish a signing
   configuration for our executable and installer that excludes upstream DLLs.
4. Use the [GitHub connector](https://docs.signpath.io/trusted-build-systems/github)
   to sign the executable before building its installer/portable archive, then
   sign the installer. Upload each unsigned artifact to GitHub Actions and use
   its artifact ID for the request; download and verify the returned artifact.
5. Run the installed runtime checks against the signed result, create final
   checksums, and publish a new release. Do not silently replace the old preview.

The current workflow builds unsigned previews. It contains no signing action or
credentials. Successful Foundation enrollment and this checklist are required
before a signed release can be produced. Windows reputation warnings can still
appear for new signed downloads; see [Microsoft's guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).
