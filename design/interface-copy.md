# PharOS interface copy

The map workspace helps someone choose a place, inspect a camera, and review a finding. It keeps the emerald, sage, and ivory identity while adapting the reference workspace's compact controls and right sidebar. The headdress, eye, and lighthouse carry the brand; the lockup needs only “PharOS.” Technical context belongs where someone asks for it.

## Primary labels

| Label | Meaning | Placement |
| --- | --- | --- |
| City | Focus, nearby cameras, history, and search | First sidebar tab |
| Camera area | Footage and evidence for the selected location | Second sidebar tab |
| Review | Find recorded footage and review its actual bytes | Third sidebar tab |
| Live nearby | Continuous feeds, each with distance from the demo focus | City camera list |
| Street image | A refreshed public still | Image overlay |
| When it happens | Reported crashes by local hour over the displayed period | Historical chart |
| Latest observation | Result for a bounded captured window | Live camera review |
| Monitor on / off | Start or pause successive window requests | Camera review control |
| Replay projection | Conditional image motion from the displayed analyzed frame | Optional overlay control |
| Search criteria | Evidence needed to answer the submitted question | Expandable recorded-search details |
| Sources & connections | Provider links, actual service states, measurement notes | Sidebar footer and connection dialog |

Result wording must retain the distinction between an unknown result and an observed absence. “Not observed” concerns the checked question and captured window. “Needs review” signals uncertainty; a model-supported candidate is not a confirmed event count. A source failure preserves the last successful timestamp rather than appearing freshly checked.

## Keep close to the evidence

Show the camera name, source mode, a concise useful age, and current analysis status. A nearby camera keeps its own name and distance; do not rename it as the selected intersection. Label historical charts with their actual period and measure. “Crash reports” in the hourly chart includes non-injury reports; “Injury crashes” names the heatmap measure. Use “Candidates” for unreviewed model results and “Reviewed” only after a person has reviewed them.

Put camera IDs, model IDs, input hash, provider request IDs, source clock limitations, feed terms, calibration limits, and full citations in **Capture details**, **Source details**, or **Sources & connections**. They remain accessible without occupying every card. Avoid stacking a tagline, eyebrow, subtitle, paragraph, and footer disclaimer around the same video.

Connection wording follows the evidence: **Connected** means the named check or recent operation succeeded; **Not verified** means configuration has not yet produced a verified operation; **Check needed** means the last success is stale; **Not connected** means unavailable or failed. Expand the row to see whether the check was service health or actual inference. Do not imply that a health badge verifies video findings.

## Layout rhythm

Use one heading and one primary action per section. Keep map controls together and evidence controls beside the video. History shows the period and available counts before explanatory prose; absent history says no matched profile, rather than zero crashes. Hourly bars expose exact counts on focus as well as hover. Preserve the last completed camera result while the next window runs. On narrow screens, the same tabs and hierarchy move into one bottom panel.

## Simplify skill availability

The requested `simplify` skill could not be retrieved from [its skills.md endpoint](https://skills.md/api/v1/skills/simplify/skill.md): it returned HTTP 404, `skill not found`, on October 9, 2026. The [public catalog](https://skills.md/api/v1/skills) returned 250 entries without that name; the [official discovery documentation](https://skills.md/docs/skills) describes authenticated remote discovery. No installation, account sign-in, or paid run was performed. This guide applies a manual simplification pass and does not claim use of an unavailable skill.
