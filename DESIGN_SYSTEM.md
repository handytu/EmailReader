# EmailReader desktop design

Adapted from the UI/UX Pro Max guidelines supplied by the user. The associated
search script and recommendation database are unavailable in this workspace.

- Product: multi-account desktop email reader, implemented with PySide6.
- Style: restrained dark workspace with three clearly separated columns.
- Palette: slate surfaces, blue actions, light text, readable secondary text.
- Typography: Segoe UI, 14px body text, 20px panel titles, 24px message titles.
- Spacing: 8px base rhythm; 44px primary controls and icon targets.
- Interaction: visible keyboard focus, stable hover geometry, named icon buttons,
  textual account status alongside color, checked filters, explicit sync feedback.
- Reading: compact rows show sender and subject; comfortable rows add preview.
- Layout: desktop minimum width 1100px; resizable columns with usable minimums.
  This application is a Windows desktop reader rather than a mobile website.
- Motion: no decorative animation; asynchronous loading does not resize controls.

Validation: regression checks, offline window checks, rendered screenshots at
1100px and 1440px using fictional accounts and messages only.
