// Platform icon set (ADR-0003): lucide-react, bundled + tree-shaken (no CDN, no
// runtime fetch — no-egress applies to assets). This is the ONE place the app's icon
// vocabulary is declared; components import from here. Size comes from `--icon-size`
// (see structure.css `.lf-iconbtn svg`), colour from `currentColor`, so icons follow
// the token layer + theme automatically.
export {
  // Theme (light / dark / system)
  Sun,
  Moon,
  Monitor,
  // Density (comfortable / compact)
  Rows2,
  Rows4,
  // Contrast (system / normal / high)
  Contrast,
  Circle,
  Disc,
  // Motion (full / reduced / system)
  Waves,
  Minus,
  Wind,
  // Rotation (on / off)
  RotateCw,
  Ban,
  // Charts (LineChart also flags the Net worth trend). The top-bar Detail toggle that once
  // used these was REMOVED — page-home §9-15 (the Home layout is a Settings control).
  LineChart,
  CandlestickChart,
  // Menu / overflow
  Menu,
  MoreHorizontal,
  // Page actions
  Pencil,
  Upload,
  Download,
  Printer,
  Plus,
  CircleCheck,
  // Destructive action (danger Button variant — reset/purge class, DESIGN-SYSTEM §5.4)
  Trash2,
  // Status
  TriangleAlert,
  // Settings → About, the social-icon row (page-help §9-bis-13).
  //
  // THESE ARE SEMANTIC GLYPHS, NOT BRAND MARKS, AND NOT BY PREFERENCE. lucide REMOVED its brand
  // icons: `Github` and `Linkedin` do not exist in the pinned 1.24.0 (checked against the installed
  // package). A brand-icon package is a NEW DEPENDENCY and CLAUDE.md forbids one without an ADR, so
  // the meaning lives in each link's accessible name and its hover/focus URL instead of in the
  // glyph. `Code` is the repository, `GitBranch` the author's profile — the pair has to be
  // distinguishable because both destinations are GitHub.
  Globe,
  Code,
  UserRound,
  GitBranch,
  Briefcase,
  Heart,
} from "lucide-react";

export type { LucideIcon } from "lucide-react";
