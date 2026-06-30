"""analysis.forensic — offline forensic measurement layer (Gate G.5).

This subpackage holds OFFLINE forensic measurement code only. It is NOT a live
runner and NOT an execution path:

  * NO real orders, NO wallet/signing/capital, NO Live S1 access.
  * NO API polling, NO live DB. /tmp artifacts only when (separately) armed.
  * Status: G.5_OFFLINE_FORENSIC_ENGINE_FEATURE_LOCKED / NOT_RUNNER_LAUNCHED.

The engine computes NOTHING on import and creates NO files on import. Its
hard execution guard (GATEG5_ARM) keeps the armed path inert; importing this
package never arms it.
"""
