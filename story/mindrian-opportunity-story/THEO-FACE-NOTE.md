# Theo face system

Theo is the outside thinker, not a mascot. The storyboard uses the canonical square-geometry face and the website's named Theo poses. Pose geometry follows `website/public/theo-face.js` and the static stage treatment in `components/home-story/FaceStill.tsx`.

The face continues from one scene into the next: rest → search → found → listening → search → challenge → decision → handover. GSAP animates the canonical eyes, slash, rules, and tile planes from the prior pose into the next, timed to the scene transition. The stage plane remains white; surrounding square tiles and planes carry evidence, assumptions, contradictions, the human decision, and handover.
