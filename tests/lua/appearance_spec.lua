-- Uso: SPEC_CASE=valid|empty lua tests/lua/appearance_spec.lua
-- HYPR_AJUSTES_DIR debe apuntar al directorio con appearance.json (o sin él).
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

-- hl falso: registra las llamadas a hl.config
local config_calls = {}
local hl = {
    config = function(cfg) config_calls[#config_calls + 1] = cfg end,
}

local applied = settings.appearance(hl)
local case = os.getenv("SPEC_CASE") or "valid"

if case == "valid" then
    check("aplica una vez", applied == 1 and #config_calls == 1)
    local cfg = config_calls[1] or {}
    local general = cfg.general or {}
    local decoration = cfg.decoration or {}
    local animations = cfg.animations or {}
    check("gaps_in", general.gaps_in == 8)
    check("gaps_out", general.gaps_out == 16)
    check("border_size", general.border_size == 3)
    check("rounding", decoration.rounding == 20)
    check("blur enabled", decoration.blur and decoration.blur.enabled == false)
    check("blur size", decoration.blur and decoration.blur.size == 5)
    check("blur passes", decoration.blur and decoration.blur.passes == 2)
    check("animations enabled", animations.enabled == false)
    local col = general.col or {}
    local active = col.active_border or {}
    check("gradiente activo color 1", active.colors and active.colors[1] == "rgba(112233ff)")
    check("gradiente activo color 2", active.colors and active.colors[2] == "rgba(445566ff)")
    check("gradiente ángulo", active.angle == 90)
    check("borde inactivo", col.inactive_border == "rgba(778899aa)")

elseif case == "empty" then -- JSON ausente o corrupto
    check("no aplica nada", applied == 0 and #config_calls == 0)

else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures > 0 then os.exit(1) end
print("OK")
