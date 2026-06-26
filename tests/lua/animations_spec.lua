-- Uso: SPEC_CASE=valid|empty lua tests/lua/animations_spec.lua
-- HYPR_AJUSTES_DIR debe apuntar al directorio con animations.json (o sin él).
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

-- hl falso: registra las llamadas a hl.animation
local anim_calls = {}
local hl = {
    animation = function(spec) anim_calls[#anim_calls + 1] = spec end,
}

local applied = settings.animations(hl)
local case = os.getenv("SPEC_CASE") or "valid"

if case == "valid" then
    check("aplica 3 leaves", applied == 3 and #anim_calls == 3)
    local by_leaf = {}
    for _, call in ipairs(anim_calls) do by_leaf[call.leaf] = call end
    check("windows leaf", by_leaf.windows ~= nil)
    check("windows speed", by_leaf.windows and by_leaf.windows.speed == 7.0)
    check("windows bezier", by_leaf.windows and by_leaf.windows.bezier == "myBezier")
    check("windows enabled", by_leaf.windows and by_leaf.windows.enabled == true)
    check("windows sin style (vacío omitido)", by_leaf.windows and by_leaf.windows.style == nil)
    check("windowsOut style presente", by_leaf.windowsOut and by_leaf.windowsOut.style == "popin 80%")
    check("fade disabled", by_leaf.fade and by_leaf.fade.enabled == false)
    check("fade bezier linear", by_leaf.fade and by_leaf.fade.bezier == "linear")

elseif case == "empty" then -- JSON ausente o corrupto
    check("no aplica nada", applied == 0 and #anim_calls == 0)

else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures > 0 then os.exit(1) end
print("OK")
