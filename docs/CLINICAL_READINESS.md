# Clinical Readiness Checklist

AURA Global is not ready for real-world patient use by code changes alone. A camera-based vital signs product may become Software as a Medical Device when it is intended for diagnosis, treatment, monitoring, or clinical decision support. Real-world launch requires evidence, controls, and approvals outside this repository.

## Life-Safety Position

- Do not use this software when someone's life, emergency care, diagnosis, triage, treatment, or monitoring depends on the output.
- Use approved medical devices and trained clinical workflows for any patient-safety decision.
- Keep `CLINICAL_USE_ENABLED=false` until validation, regulatory clearance, cybersecurity review, quality-system controls, and clinical governance are complete.
- Treat every displayed value as research telemetry unless the exact deployed version has been validated for the exact intended use and population.

## Product Gate

- Define the exact intended use, user population, environment, contraindications, and failure modes.
- Decide whether the product is wellness-only, clinical decision support, remote patient monitoring, or a diagnostic/monitoring medical device.
- Lock production algorithms, thresholds, UI claims, and supported camera/lighting conditions before validation.
- Remove or qualify any unverified accuracy, success-rate, or safety claims.
- Define emergency-use exclusions and make them visible in the UI, API, operator training, and deployment documents.

## Accuracy Gate

- Validate against reference devices such as ECG or clinically accepted pulse oximetry for heart rate and appropriate respiratory reference methods for respiration rate.
- Test across skin tones, ages, sex, lighting conditions, cameras, motion levels, facial hair, glasses, and common real-world environments.
- Report MAE, RMSE, bias, limits of agreement, missing-result rate, false pass rate, and subgroup performance.
- Require prospective validation data before patient-facing use.
- Keep failure rejection strict: a rejected scan is safer than a misleading number.

## Engineering Gate

- Keep timestamp-aware signal processing enabled.
- Require production quality gates for usable duration, signal quality, sample reliability, heart-rate agreement, and respiration detection.
- Store audit logs for scan status, quality, reliability, algorithm version, and operator actions.
- Add automated tests with synthetic signals and recorded validation fixtures.
- Add security hardening before deployment: authentication, rate limits, HTTPS, secret rotation, and privacy review.
- Maintain fail-closed behavior: unclear signal, missing validation, or disabled clinical mode must not produce a clinical success state.

## Regulatory Gate

- Review FDA Software as a Medical Device guidance for U.S. launch.
- Review FDA clinical decision support guidance if the product influences clinician or patient decisions.
- Review applicable EU MDR, UKCA, Health Canada, GCC, or local-market medical device requirements before multinational release.
- Establish a quality management system, risk management file, software lifecycle process, usability file, cybersecurity file, and post-market monitoring plan.

## Current Implementation Safeguards

- The backend rejects scans below production quality and reliability thresholds.
- The signal processor resamples by real timestamps instead of assuming perfect camera FPS.
- The DSP path requires agreement between spectral and autocorrelation estimates.
- The UI displays sample reliability and does not silently treat weak scans as successful.
- The backend exposes `clinical_use_enabled` and safety notices in API/WebSocket responses.
- The default `.env` keeps `CLINICAL_USE_ENABLED=false`.

## References

- FDA Software as a Medical Device: https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd
- FDA Clinical Decision Support Software: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
- FDA Artificial Intelligence in Software as a Medical Device: https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-software-medical-device
