# Tabs and Mountains, v9.3.0

Approved direction: Tabs icon from the frontend-design concept sheet, paired
with the Mountains title bar selected by the user.

- Editable native icon: `resources/app-icon.svg`; rendered Windows assets:
  `resources/app-icon.png` and `resources/app-icon.ico` (16 through 256px).
- Project background: `resources/titlebar-mountains.png`.
- Background created using the built-in ImageGen tool, copied into the project.
  The icon was reconstructed as editable SVG for crisp small-size rendering.

Background generation prompt:

> Create a single background asset for the Mountains option of a dark desktop application title bar. Wide panoramic landscape 1536x512, sophisticated minimalist cinematic layered mountain silhouettes in dark navy blue, misty cool blue distance, a modest soft blue glow near the horizon at center. Several overlapping mountain ridges extend all across the frame. Foreground near-black navy #090F16, middle layers #122B47, distant layers #345F87. Darken the far left and far right considerably to provide contrast for white UI text and window controls that will be added in code. Keep mountain ridge detail concentrated in the middle horizontal band, with restrained soft atmosphere, no bright highlights. This will be vertically compressed into a thin 44px title-bar background, so favor readable broad silhouettes rather than fine details. No text, no logo, no icons, no borders, no UI, no watermark, no people. The image itself is only the reusable mountain background.

The app renders a middle crop of the background, then paints real labels and
buttons above it. Controls are never baked into the background image.
