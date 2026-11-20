getgenv().Configuration = {
    ["Mode"]                   = "Gem",        -- Event | Story | Event (Fool's Hunt with the Honey method)
    ["Event Join By"]          = "Matchmaking",  -- Matchmaking (queue with others, solo when no team comes) | Solo
    ["Event getgenv Wait"] = 90,             -- seconds in the queue before going solo
    ["Event Summon"]           = true,           -- after every match: back to the lobby, spin the event banner with its coins
    ["Event Keep Coins"]       = 0,              -- never spin below this many event coins
    ["Equip Event Units"]      = true,           -- equip every event banner unit you own instead of Equip Best (coin boost)
    ["Event Farms"]            = 5,              -- C.E.O. / Bulby to place, 5-6; 3 placements stay for Honey, the rest kill
    ["Event Idols"]            = 1,              -- Idols to place (cheaper placing and upgrading)
    ["Event Cards"]            = { "Attack", "Attack Speed", "Yen", "Event Currency", "Boss Damage", "Range", "Random Blessings",
        "Ability Cooldown", "Secret Drop Rate", "Spellproof Enemies", "Unit Cost", "Enemy Regen", "Enemy Shield",
        "Enemy Passives", "Explosive Deaths", "Enemy Health", "Random Curses", "Enemy Speed", "Plated Enemies",
        "Resistant Enemies", "New Path" },       -- card vote order, top first
    ["Wanted Units"]           = {},             -- e.g. { "speedwagon" }, summoned with gems
    ["Banner"]                 = "EventClover",  -- EventClover | Legacy, the banner Wanted Units are summoned on
    ["Summon"]                 = "Gems x10",     -- Gems x1 | Gems x10
    ["Keep Gems"]              = 0,              -- never summon below this many gems
    ["Auto Sell Rarities"]     = { "Rare", "Epic" }, -- the game's auto-sell for summons, so event spins don't fill storage
    ["Auto Claim"]             = false,           -- daily reward, battle pass, quests, missions, level rewards
    ["Codes"]                  = {},             -- redeemed once per lobby server, e.g. { "CODE1", "CODE2" }
    ["Place Point"]            = 50,             -- % along the enemy path: 0 = enemy spawn, 100 = your base
    ["Auto Upgrade"]           = true,
    ["Auto Abilities"]         = true,
    ["Auto Skip Waves"]        = true,
    ["When Done"]              = "Stay",         -- Stay | Kick
    ["White Screen"]           = false,          -- no black status screen
    ["FPS Lock"]               = ,             -- cap FPS, 0 = off
    ["Delete Enemies"]         = false,
    ["Delete Map"]             = false,
    ["Boost FPS"]              = true,           -- matches only: strip lighting, shadows, glow, particles, decals, textures
    ["Horst"]                  = true,           -- report progress to Horst, at most once a minute (needs Horst's script)
    ["Webhook"]                = "7",             -- Discord webhook URL
}
_G.Authorize = "QUJsHCeVcgghVmfYkXvomROJJoBALnKa"
loadstring(game:HttpGet("https://api.luarmor.net/files/v4/loaders/beeedd27df16c4072f12728f48439121.lua"))()
