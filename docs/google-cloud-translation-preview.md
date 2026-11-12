# Google Cloud Translation for the Canadian Editorial preview

This integration translates **only** the seven pages under `previews/canadian/`.
It does not change the published Home, Projects, Certifications, Contact, or
published case studies. The GitHub Pages site calls no Google Cloud API from
the browser and holds no Google Cloud secrets.

## Setup once

1. In Google Cloud Console, select or create a **billing-enabled Google Cloud
   project**, then enable **Cloud Translation API**.
2. Create a service account for this build, granting the narrow
   **Cloud Translation API User** role (typically
   `roles/cloudtranslate.user`) on that project.
3. Configure **Workload Identity Federation (GitHub Actions OIDC)** and allow
   only `oba17/Oba` to impersonate this service account. Restrict the provider
   to this repository using an attribute condition such as
   `assertion.repository == 'oba17/Oba'`. No downloadable JSON key is needed.
4. In GitHub repository settings, **Settings → Secrets and variables → Actions**,
   set:
   - **Repository variable** `GCP_TRANSLATION_PROJECT_ID`: your Google Cloud
     project **ID** (not its display name).
   - **Repository secret** `GCP_WIF_PROVIDER`: the full Workload Identity
     Provider resource name, e.g.
     `projects/123456789/locations/global/workloadIdentityPools/POOL/providers/PROVIDER`.
     The leading project number is numeric.
   - **Repository secret** `GCP_TRANSLATION_SERVICE_ACCOUNT`: the complete
     service-account email address.
5. Under **Actions**, manually run
   **Generate French Portfolio Preview (Google Cloud Translation)**.
   This action uses Google Cloud authentication to translate text from seven
   preview pages, writes versioned JSON dictionaries into
   `previews/canadian/assets/translations/`, and commits only these JSON
   translation files. Inspect the action log for a successful build.

## How the website uses it

The shared preview header shows **EN | FR**. Before the translation dictionaries
exist, French remains disabled rather than claiming to be fully translated.
After a successful action run, selecting FR switches to the complete
Google-generated text for the current page; navigation retains the preference.
The live portfolio stays English-only until separately approved for publishing.

## Quality control

Google Translation is automated, not an editorial verification service.
Review French-Canadian terminology, product and certification names, figures,
quoted testimonials, architecture descriptions, diagram labels and PDF/image
content before publishing any bilingual version to the main portfolio.

Re-run the workflow after editing any of the seven preview pages; the generated
translations are a snapshot and are not regenerated automatically. Translation
API usage is billable. Configure Google Cloud budgets and quotas appropriately.

Official setup references:
- https://cloud.google.com/translate/docs/setup
- https://cloud.google.com/translate/docs/translate-text
- https://github.com/google-github-actions/auth
