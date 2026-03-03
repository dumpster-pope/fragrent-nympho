"""
Prompt Agent — Smart combinatorial art prompt generator.

Zero external dependencies. No API keys. No internet required.

Uses per-component cooldown windows, subject category rotation, style medium
rotation, and palette temperature alternation to guarantee every prompt is
visually and conceptually distinct from recent history.

Cooldown guarantees (with current list sizes):
  Subject     — 120 subjects, 70-run cooldown → always 50+ fresh options
  Style       — 60 styles,    50-run cooldown → always 10+ fresh options
  Environment — 50 envs,      35-run cooldown → always 15+ fresh options
  Mood        — 30 moods,     24-run cooldown → always 6+ fresh options
  Palette     — 30 palettes,  24-run cooldown → always 6+ fresh options
  Closer      — 20 closers,   14-run cooldown → always 6+ fresh options
"""

import logging
import random

log = logging.getLogger("art_bot")

# ── Cooldown windows ──────────────────────────────────────────────────────────

COOLDOWNS = {
    "subject":     70,
    "environment": 35,
    "style":       50,
    "mood":        24,
    "palette":     24,
    "closer":      14,
}

CATEGORY_COOLDOWN = 3   # same subject category can't appear in last 3 runs
MEDIUM_COOLDOWN   = 2   # same style medium can't appear in last 2 runs
TEMP_COOLDOWN     = 2   # same palette temperature can't appear in last 2 runs

# ── Subject library — organised by thematic category ─────────────────────────

SUBJECTS_BY_CATEGORY = {

    "ARCHITECTURAL": [
        "an ancient lighthouse assembled from crystallised memories",
        "a cathedral sculpted entirely from frozen ocean waves",
        "a clockwork forest where every tree displays a different era",
        "a city suspended inside an enormous soap bubble over the void",
        "a vast library whose books drift like paper lanterns in still air",
        "a mechanical garden where iron flowers bloom only at midnight",
        "a staircase of glowing marble that spirals up into deep space",
        "a train station perched at the absolute edge of the known world",
        "a tower built from the fossilised bones of dead languages",
        "a bridge constructed from the interlocked silhouettes of dancers",
        "a monastery carved directly into the face of a thunderstorm",
        "a crumbling opera house slowly being swallowed by an ancient forest",
        "a cathedral made entirely of stacked hourglasses, each one running",
        "a vast greenhouse on a frozen planet, lit from within like a lantern",
        "an observatory whose telescope points inward instead of outward",
        "a palace whose walls are compressed thunderclouds held in suspension",
        "a parliament chamber growing inside the hollow of a giant sequoia",
        "a watchtower built on the back of a slowly walking stone giant",
        "an underground city carved into the lining of an enormous geode",
        "a concert hall built inside a hollowed-out iceberg adrift at sea",
        "a hermitage balanced on a sea stack accessible only at low tide",
        "a series of gates each opening onto a completely different season",
        "a covered market in a drowned city glimpsed through crystal-clear water",
        "a cathedral of bees whose wax cells form every window and vault",
    ],

    "FIGURATIVE": [
        "a musician whose instrument releases clouds of coloured sound",
        "a painter whose every brushstroke becomes a living creature",
        "a clockmaker who repairs broken moments stolen from time itself",
        "a child who discovers a hidden door inside the cast shadow of a tree",
        "a scholar translating manuscripts written in light on cave walls",
        "a samurai guarding the entrance to a portal made of cascading water",
        "a lone astronaut discovering a blooming greenhouse on a dead moon",
        "an old cartographer drawing maps of places that do not exist yet",
        "a diver descending into a sea made entirely of liquid amber",
        "a weaver whose tapestry depicts the future as it is happening",
        "a street musician playing a song that makes memories visible",
        "a woman standing at the threshold of a door made of moving water",
        "a glassblower shaping new constellations from a single sustained breath",
        "a letter-writer composing correspondence for people not yet born",
        "an archivist cataloguing the recorded sounds of extinct animals",
        "a ferryman carrying shadows across a river of suspended time",
        "a seamstress stitching torn hours back together by candlelight",
        "a mapmaker charting the interior landscape of a long grief",
        "a child teaching an enormous, ancient god how to skip stones",
        "an elder knitting a blanket from the unravelling threads of memory",
        "a blind sculptor working from sound alone in a resonant cave",
        "a gardener tending a field of flowers that bloom only in dreams",
        "a merchant selling the last surviving specimens of a lost colour",
        "an astronomer reading a star chart tattooed across her forearm",
    ],

    "NATURE": [
        "a luna moth the size of a city hovering over candlelit streets",
        "a colossal whale drifting through the clouds above a medieval city",
        "a phoenix being reborn from the smouldering ashes of a library",
        "a forest in which every shadow has a life entirely its own",
        "a river of liquid starlight flowing uphill through stone channels",
        "an island that materialises only during total solar eclipses",
        "a flock of paper cranes migrating across a winter sky at dusk",
        "a forest of bioluminescent trees reflected in a perfectly still lake",
        "a meadow where every flower is a different extinct species",
        "a black fox with a tail made of northern lights crossing a frozen lake",
        "a cloud of monarch butterflies forming the silhouette of a vanished forest",
        "a sea of moon jellyfish glowing beneath a winter thunderstorm",
        "a whale skeleton draped in living anemones on the ocean floor",
        "a flock of starlings forming the precise outline of a demolished city",
        "an ancient tortoise whose shell has become a small island ecosystem",
        "a pod of narwhals passing in formation beneath transparent arctic ice",
        "a leviathan barely visible beneath the surface of a sea of cloud",
        "mushrooms the size of houses rising from a mossy valley after rain",
        "a spiral of migrating birds seen from directly below",
        "twin moons casting double shadows over an alien salt flat",
        "a desert made entirely of shattered antique mirrors",
        "a coral reef flowering through the skeletal ruins of a skyscraper",
        "a glacier releasing its last sealed river at the exact moment of dawn",
        "a forest where every tree holds a different extinct bird in song",
    ],

    "SCENE": [
        "a bazaar where merchants sell bottled human emotions",
        "an underwater concert hall packed with singing deep-sea creatures",
        "an orchestra playing silently inside the eye of a hurricane",
        "a carnival at the end of the universe, lit by dying stars",
        "a night market where every stall sells a different kind of silence",
        "a floating lantern festival observed from directly beneath the water",
        "a village fair held in the ruins of a decommissioned space elevator",
        "an auction house selling sealed jars of rare and violent thunderstorms",
        "a candlelit underground supper club for nocturnal creatures only",
        "a riverside market where people trade complete stories for other stories",
        "a wandering theatre troupe performing Shakespeare on a moving train",
        "a symposium of cartographers disputing maps of imaginary continents",
        "a pilgrimage of thousands climbing a staircase that descends into cloud",
        "a chess match played on a board the size of a continent by giants",
        "a marketplace where dreamers trade memories for new nightmares",
        "a midnight procession of lanterns through the ruins of a drowned city",
        "a travelling circus whose performers are all former astronomers",
        "a feast laid at the long table of a glacier before it retreats",
        "a festival of lights in a subterranean cathedral known only to miners",
        "a night bazaar where every vendor sells a different species of quiet",
    ],

    "RUIN": [
        "an abandoned generation ship consumed by bioluminescent moss",
        "a sunken cathedral glimpsed through fathoms of glowing green water",
        "a city reclaimed by vines and flowering trees after centuries of silence",
        "the ruins of a space station wrapped in morning glory and moss",
        "an underground station where a phantom train still runs on schedule",
        "a vast hotel ballroom slowly consumed by a colony of bats and ferns",
        "a rusted radio telescope buried to its dish in drifting red sand",
        "a nuclear cooling tower converted to a hanging garden by generations of birds",
        "a flooded amphitheatre where fish now perform for empty stone seats",
        "a Victorian conservatory collapsed into its own greenhouse jungle",
        "a capsized ocean liner becoming an artificial reef at forty fathoms",
        "a derelict drive-in cinema whose screen is now a canvas for swallows",
        "an abandoned polar research station buried to its windows in ice",
        "a ghost town of miners' cabins half-swallowed by a new lava field",
        "the colonnade of a long-demolished temple standing alone in a wheat field",
        "a crumbling aqueduct used as a footpath by migrating mountain goats",
        "a lighthouse whose lamp still turns though the keeper vanished centuries ago",
        "the prow of a wooden sailing ship emerging from the face of a dune",
        "a Roman road stretching ruler-straight through a forest that swallowed everything else",
        "an overgrown mansion whose ballroom floor has become a reflecting pool",
    ],

    "COSMIC": [
        "a planet whose rings are made from the compressed light of a supernova",
        "two dying stars in a final gravitational waltz",
        "a nebula lit from within by a newly ignited star cluster",
        "an asteroid covered in petroglyphs made by a long-vanished civilisation",
        "the surface of a rogue planet wandering through interstellar darkness",
        "a gas giant's perpetual storm seen close enough to feel the scale",
        "a comet's nucleus lit only by its own ion tail at perihelion",
        "the frozen ocean of a moon lit by its parent gas giant's pale glow",
        "the moment of first contact between two tectonic plates becoming mountains",
        "the precise moment before a black hole begins to evaporate in light",
        "a binary pulsar system seen from the surface of a nearby world",
        "a ring world seen edge-on against the star it orbits",
        "the terminator of a tidally locked planet — eternal day and eternal night",
        "a neutron star magnetar in the act of releasing a soft gamma burst",
        "a system of moons locked in orbital resonance, braiding their paths",
        "the void between superclusters — no star within a billion light-years",
        "the moment a stellar nursery collapses and first light appears",
        "a dead star field seen from a planet where the night never truly ends",
        "the accretion disc of a stellar-mass black hole glowing in iron emission lines",
        "a time-lapse of a thousand years of forest growing, dying, and regrowing",
    ],
}

# ── Environment library ───────────────────────────────────────────────────────

ALL_ENVIRONMENTS = [
    # Atmospheric / meteorological
    "bathed in the violet light of three simultaneous moons",
    "ringed by storm clouds crackling with chains of golden lightning",
    "emerging from dense, slow-moving fog at the edge of reality",
    "caught in the moment before a storm breaks, the air charged and still",
    "in the long blue shadow of a glacier at the end of summer",
    "on the surface of a storm-cloud seen from above, lit by continuous lightning",
    "at the heart of a desert sandstorm, the world reduced to gold and amber",
    "in a bamboo forest during monsoon, the sound overwhelming, the light green-silver",
    "at the instant a dam breaks and water begins its first unstoppable rush",
    "seen through the viewfinder of a field camera on a 19th-century expedition",
    # Light and time of day
    "at the precise moment of a blazing sunrise over an alien horizon",
    "frozen mid-collapse, every grain of dust suspended in raking light",
    "at the hour when daylight and darkness are perfectly balanced",
    "seen through rain-streaked glass, the outside world blurred and soft",
    "lit from below by the glow of something vast and unseen beneath",
    "at the exact border between a snowfield and a red desert",
    "in the moment after an earthquake when the dust still hangs suspended",
    "under the shelter of a cedar that has grown for three thousand years",
    "at the terminator line between sunlit hemisphere and shadow",
    "surrounded by the remnants of an ancient bonfire, still faintly glowing",
    # Water and ice
    "surrounded by millions of glowing fireflies frozen mid-flight",
    "reflected infinitely in a surface of still, perfectly black water",
    "submerged under a shallow layer of perfectly transparent water",
    "inside a vast sea cave lit only by bioluminescent surf",
    "on the floor of a dead sea, the shore impossibly distant",
    "inside the hollow of a wave at the moment before it breaks",
    "beneath a ceiling of stalactites studded with luminescent minerals",
    "deep inside a glacier, the blue ice walls glowing with trapped millennia",
    "at the bank of a river of meltwater from a retreating glacier",
    # Landscape
    "half-reclaimed by encroaching jungle, lianas crawling over everything",
    "glimpsed through a curtain of falling cherry blossoms",
    "under a sky filled with enormous floating crystalline formations",
    "dissolving at the edges into cascades of geometric copper particles",
    "at the centre of a vast natural amphitheatre of wind-carved red stone",
    "at the edge of a sheer cliff overlooking an ocean of slow clouds",
    "inside a narrow canyon where the rock strata glow with mineral colour",
    "surrounded by a circle of ancient standing stones at the winter solstice",
    "at the point where a river disappears underground into total darkness",
    "consumed by glowing bioluminescent vines at the last moment of dusk",
    "in a gorge so deep that the sky above is a thin ribbon of blue",
    "on the back of a creature large enough to carry an entire ecosystem",
    "at the edge of a salt flat at the exact moment of a heat mirage",
    "in a narrow alley of a medieval city during a festival of coloured lights",
    "at the top of a mesa at the precise moment the last shadow retreats at dawn",
    "in the remains of a city the morning after a long siege ended in peace",
    "at the edge of a peat bog at twilight, the surface mirror-still",
    "in a flooded forest where the treetops form islands above black water",
    "in the eye of a waterspout passing over a turquoise tropical lagoon",
    "at the precise border where a pine forest meets an open snowfield",
]

# ── Style library — organised by medium ──────────────────────────────────────

STYLES_BY_MEDIUM = {

    "CLASSICAL_PAINTING": [
        "painted in heavy impasto oils with Baroque chiaroscuro and deep shadows",
        "in the style of the Hudson River School, vast and romantically lit",
        "painted in the manner of Caspar David Friedrich, solitary and sublime",
        "painted as a lush Pre-Raphaelite oil, jewel-toned and botanically precise",
        "rendered as a richly layered Symbolist painting from the 1890s",
        "painted as Japanese nihonga on silk, gold leaf accents and soft gradients",
        "in the Flemish Golden Age oil tradition, luminous and meticulously observed",
        "as a Byzantine egg-tempera icon, gold ground, hieratic and still",
        "in the manner of a Mughal miniature on paper, exquisitely detailed",
        "as a Northern Renaissance panel painting in mixed egg-tempera and oil",
        "in the French Academic Salon tradition, technically flawless and monumental",
        "in the manner of Venetian oil painting, rich imprimatura with cool glazes",
    ],

    "MODERN_PAINTING": [
        "in the nightmarish surrealist oil style of Beksinski, raw and haunting",
        "rendered as a loose, luminous plein-air oil sketch",
        "illustrated as a luminous Art Nouveau poster by Alphonse Mucha",
        "depicted as a bold Soviet Constructivist propaganda lithograph",
        "depicted as a hand-lettered psychedelic 1967 concert poster",
        "as a gestural Abstract Expressionist oil, paint flung and dragged",
        "in the Fauvist tradition, colour pushed far beyond the natural",
        "as a naive primitive oil of the kind made by untrained Sunday painters",
        "rendered entirely in shades of grey as a Baroque en grisaille study",
        "in the controlled drip and pour style of mid-century lyrical abstraction",
        "as a hard-edge colour field painting, flat zones of saturated pigment",
        "as a Dada photomontage composed from cut newspaper and painted wash",
    ],

    "PHOTOGRAPHY": [
        "shot on large-format film, rich tonal range and deep focus",
        "photographed on Kodachrome slide film, saturated and grain-heavy",
        "captured on medium-format black-and-white film with wide dynamic range",
        "shot on expired 35mm Portra film, soft colours and organic grain",
        "photographed with a long exposure at blue hour, light trails and stillness",
        "captured with a vintage Hasselblad on Tri-X pushed to 3200 ISO",
        "taken with a pinhole camera, soft and dreamlike with extreme depth of field",
        "on wet collodion ambrotype glass, tonal inversion and silver sheen",
        "as a daguerreotype, mercury silver on polished copper, mirror-reversed",
        "as a cyanotype contact print, prussian blue and white, botanical scale",
        "on infrared film, foliage bleached white, skies black, skin luminous",
        "on a glass plate negative, tonal compression and silver fog in the shadows",
    ],

    "PRINTMAKING": [
        "rendered as a hand-pulled Japanese woodblock print, flat and graphic",
        "composed as a hyperdetailed Gustave Dore steel engraving",
        "depicted as a hand-screen-printed two-colour risograph illustration",
        "as a bold reduction linocut in three colours on handmade paper",
        "as a mezzotint, the deepest blacks velvety, the lights scraped bright",
        "as a Victorian natural history copperplate engraving with hand tinting",
        "as a fine etching with dense drypoint burr for shadow and texture",
        "as a screen print in four flat colours on kraft card",
        "as a woodcut in the tradition of German Expressionism, raw and angular",
        "as a collagraph printed on dampened Japanese tissue paper",
    ],

    "ILLUSTRATION": [
        "in the style of a Studio Ghibli background painting, lush and atmospheric",
        "illustrated with the delicate watercolour washes of Arthur Rackham",
        "in the style of an N.C. Wyeth adventure illustration, dramatic and heroic",
        "created in the exact ligne claire style of Jean Giraud (Moebius)",
        "illustrated as a vintage 1970s science fiction paperback cover",
        "illustrated as a richly detailed medieval illuminated manuscript",
        "depicted as a stained-glass window in the High Gothic tradition",
        "designed as a bold Art Deco travel poster from the 1930s",
        "as a Golden Age botanical watercolour with taxonomic precision",
        "as an Edwardian pen-and-ink full-page magazine illustration",
        "as a mid-century children's picture book illustration in gouache",
        "as a 1950s mid-century editorial spread in two-tone graphic style",
        "as a hand-rendered theatrical backdrop from a 1920s opera production",
        "in the manner of a Golden Age fairy-tale illustration by Edmund Dulac",
    ],

    "DRAWING": [
        "drawn in precise cross-hatched ink in the tradition of Albrecht Durer",
        "as a silverpoint drawing on prepared ground, delicate and permanent",
        "as a red chalk anatomical study in the Renaissance tradition",
        "as a charcoal drawing on toned paper, highlights lifted with a putty rubber",
        "as a rapid field sketch in graphite with handwritten annotations",
        "as a meticulous architectural pencil drawing, ruled and dimensioned",
        "as a conte crayon landscape with sweeping tonal masses",
        "as a wash drawing using iron gall ink diluted to twenty tones",
        "as a sketchbook page covered in overlapping studies and first thoughts",
        "as a preparatory cartoon in charcoal, energetic and unresolved",
    ],
}

# ── Palette library — organised by colour temperature ─────────────────────────

PALETTES_BY_TEMP = {

    "WARM": [
        "palette of deep indigo, burnt sienna, and pale gold",
        "warm palette of amber, rust, and candlelight yellow",
        "rich palette of emerald, midnight blue, and aged bronze",
        "earthy palette of ochre, umber, and dusty rose",
        "jewel palette of deep burgundy, forest green, and old gold",
        "palette of saffron, terracotta, and river sand",
        "palette of cardinal red, aged black, and parchment cream",
        "palette of copper, moss green, and raw sienna",
        "sunset palette of warm gold, deep violet, and rose",
        "palette of tobacco brown, bone white, and raw ochre",
    ],

    "COOL": [
        "cold palette of steel blue, grey-violet, and white",
        "washed-out palette of faded lavender, cream, and moss",
        "stark palette of Payne's grey, raw umber, and chalk white",
        "ice palette of pale blue, silver-grey, and absolute white",
        "palette of slate blue, sage green, and birch-bark white",
        "Arctic palette of grey, pale aquamarine, and moonlight white",
        "palette of cobalt blue, ash grey, and moonlight",
        "palette of sea-glass green, gunmetal, and foam white",
        "palette of indigo, dove grey, and cool linen",
        "palette of midnight blue, teal, and pale silver",
    ],

    "NEUTRAL": [
        "muted palette of sage green, terracotta, and off-white",
        "tender palette of blush, ivory, and pale celadon green",
        "muted sepia palette of taupe, sand, and aged linen",
        "warm grey palette of dusk pink, stone, and champagne",
        "palette of ash, sand, and pale driftwood",
        "palette of ecru, pewter, and graphite",
        "palette of straw, stone, and cool shadow",
        "palette of natural linen, soft umber, and warm grey",
    ],

    "DRAMATIC": [
        "high-contrast palette of pure black, crimson, and silver",
        "dramatic palette of charcoal, electric teal, and copper",
        "palette of electric indigo, acid yellow, and absolute black",
        "palette of deep viridian, cadmium orange, and pitch black",
        "palette of ultramarine, crimson lake, and raw sienna on black",
        "palette of vermilion red, midnight navy, and hammered silver",
        "palette of phosphorescent green, void black, and bone white",
        "palette of violent magenta, charcoal, and chrome yellow",
    ],
}

# ── Mood library ──────────────────────────────────────────────────────────────

ALL_MOODS = [
    # Serene
    "evoking profound melancholy and quiet, aching beauty",
    "exuding warmth, safety, and last-light nostalgia",
    "suffused with a bittersweet longing for something just out of reach",
    "humming with quiet magic, as if the world is holding its breath",
    "dreamlike and soft, like a memory seen through frosted glass",
    "serene yet subtly unsettling, like a half-remembered dream",
    "filled with the stillness of a place where something significant just ended",
    "weighted with the particular sadness of beauty that is ending",
    "pervaded by the loneliness of the last light on an empty day",
    "carrying the quiet of a place that has been empty for a very long time",
    # Dramatic / tense
    "filled with electric tension just before a great transformation",
    "charged with eerie cosmic dread and awe at infinite scale",
    "wrapped in mystery, secrets barely visible at the very edges",
    "taut with the held breath before an irreversible act",
    "carrying the stillness and gravity of a place struck by lightning",
    "alive with a sense of something ancient waking after long sleep",
    "dense with foreboding that is worse than the thing feared",
    "suffused with the controlled power of forces about to be released",
    # Joyful / transcendent
    "bursting with joyful, barely-contained chaos and colour",
    "alive with spiritual transcendence and inner light",
    "radiant with the uncomplicated happiness of living things in motion",
    "effervescent with the specific joy of a day that exceeded all expectation",
    # Ancient / mysterious
    "radiating a sense of ancient, utterly forgotten wonder",
    "raw and honest, stripped of sentimentality, deeply human",
    "pervaded by the quiet presence of something felt but not seen",
    "dense with layered meaning that reveals itself slowly",
    "carrying the deep patience of geological time",
    "heavy with the accumulated weight of lost civilisations",
    "threaded with the strange dignity of things that have outlasted their purpose",
    "alive with the specific sadness of a language with no remaining speakers",
]

# ── Closer library ────────────────────────────────────────────────────────────

ALL_CLOSERS = [
    "Fine detail throughout, strong sense of depth and atmosphere.",
    "Confident brushwork, rich surface texture, compelling composition.",
    "Precise linework, balanced tonal values, arresting focal point.",
    "Loose gestural marks, luminous light, cohesive visual language.",
    "Meticulous rendering, expressive use of shadow, timeless feel.",
    "Bold shapes, layered colour, striking negative space.",
    "Intimate scale, careful observation, quiet emotional weight.",
    "Sweeping composition, dramatic contrast, immersive atmosphere.",
    "Unified tonal key, restrained palette, authoritative mark-making.",
    "Complex layering, warm underpainting showing through cool glazes.",
    "High dynamic range, long tonal scale, sharp edges yielding to soft.",
    "Flat planes of colour, deliberate cropping, graphic clarity.",
    "Close observation, micro-detail in shadow, air between objects.",
    "Single light source, deep shadow, classical three-value structure.",
    "Warm foreground, cool recession, atmospheric perspective at work.",
    "Precise tonal mapping, controlled edges, classical balance.",
    "Minimal composition, maximum resonance, nothing wasted.",
    "Decisive negative space, precise silhouette, economy of means.",
    "Energetic underdrawing visible through translucent upper layers.",
    "Dense surface, complex history of mark-making, restless life.",
]


# ── Core generation function ──────────────────────────────────────────────────

def generate_fresh_prompt(history: list) -> tuple:
    """
    Generate a unique art prompt using cooldown tracking and category rotation.

    Args:
        history: List of history dicts from art_bot._load_history().

    Returns:
        (prompt_str, components_dict) — always returns a result.
    """
    recent = [h for h in history if isinstance(h, dict)]

    # ── Subject ───────────────────────────────────────────────────────────────
    used_subjects = {
        h.get("subject_full", "")
        for h in recent[-COOLDOWNS["subject"]:]
        if h.get("subject_full")
    }
    recent_cats = [
        h.get("subject_category", "")
        for h in recent[-CATEGORY_COOLDOWN:]
        if h.get("subject_category")
    ]
    all_cats = list(SUBJECTS_BY_CATEGORY.keys())
    available_cats = [c for c in all_cats if c not in recent_cats] or all_cats

    chosen_cat = random.choice(available_cats)
    subject_pool = [s for s in SUBJECTS_BY_CATEGORY[chosen_cat] if s not in used_subjects]
    if not subject_pool:
        subject_pool = SUBJECTS_BY_CATEGORY[chosen_cat]
    subject = random.choice(subject_pool)

    # ── Style ─────────────────────────────────────────────────────────────────
    used_styles = {
        h.get("style_full", "")
        for h in recent[-COOLDOWNS["style"]:]
        if h.get("style_full")
    }
    recent_mediums = [
        h.get("style_medium", "")
        for h in recent[-MEDIUM_COOLDOWN:]
        if h.get("style_medium")
    ]
    all_mediums = list(STYLES_BY_MEDIUM.keys())
    available_mediums = [m for m in all_mediums if m not in recent_mediums] or all_mediums

    chosen_medium = random.choice(available_mediums)
    style_pool = [s for s in STYLES_BY_MEDIUM[chosen_medium] if s not in used_styles]
    if not style_pool:
        style_pool = STYLES_BY_MEDIUM[chosen_medium]
    style = random.choice(style_pool)

    # ── Palette ───────────────────────────────────────────────────────────────
    used_palettes = {
        h.get("palette_full", "")
        for h in recent[-COOLDOWNS["palette"]:]
        if h.get("palette_full")
    }
    recent_temps = [
        h.get("palette_temp", "")
        for h in recent[-TEMP_COOLDOWN:]
        if h.get("palette_temp")
    ]
    all_temps = list(PALETTES_BY_TEMP.keys())
    available_temps = [t for t in all_temps if t not in recent_temps] or all_temps

    chosen_temp = random.choice(available_temps)
    palette_pool = [p for p in PALETTES_BY_TEMP[chosen_temp] if p not in used_palettes]
    if not palette_pool:
        palette_pool = PALETTES_BY_TEMP[chosen_temp]
    palette = random.choice(palette_pool)

    # ── Environment ───────────────────────────────────────────────────────────
    used_envs = {
        h.get("environment_full", "")
        for h in recent[-COOLDOWNS["environment"]:]
        if h.get("environment_full")
    }
    env_pool = [e for e in ALL_ENVIRONMENTS if e not in used_envs] or ALL_ENVIRONMENTS
    environment = random.choice(env_pool)

    # ── Mood ──────────────────────────────────────────────────────────────────
    used_moods = {
        h.get("mood_full", "")
        for h in recent[-COOLDOWNS["mood"]:]
        if h.get("mood_full")
    }
    mood_pool = [m for m in ALL_MOODS if m not in used_moods] or ALL_MOODS
    mood = random.choice(mood_pool)

    # ── Closer ────────────────────────────────────────────────────────────────
    used_closers = {
        h.get("closer_full", "")
        for h in recent[-COOLDOWNS["closer"]:]
        if h.get("closer_full")
    }
    closer_pool = [c for c in ALL_CLOSERS if c not in used_closers] or ALL_CLOSERS
    closer = random.choice(closer_pool)

    # ── Assemble ──────────────────────────────────────────────────────────────
    prompt_str = (
        f"{subject.capitalize()}, {environment}. "
        f"{style.capitalize()}, {palette}. "
        f"{mood.capitalize()}. {closer}"
    )

    components = {
        # Values for caption building and image generation
        "subject":          subject,
        "environment":      environment,
        "style":            style,
        "mood":             mood,
        "palette":          palette,
        "closer":           closer,
        # Full strings saved to history for cooldown lookups next run
        "subject_full":     subject,
        "environment_full": environment,
        "style_full":       style,
        "mood_full":        mood,
        "palette_full":     palette,
        "closer_full":      closer,
        # Category metadata for rotation tracking
        "subject_category": chosen_cat,
        "style_medium":     chosen_medium,
        "palette_temp":     chosen_temp,
    }

    log.info(
        f"Prompt [{chosen_cat} / {chosen_medium} / {chosen_temp}]: "
        f"{prompt_str[:90]}…"
    )
    return prompt_str, components
