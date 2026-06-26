-- Uso: SPEC_CASE=animated|static_only|mixed|empty lua tests/lua/wallpaper_spec.lua
-- HYPR_AJUSTES_DIR debe apuntar al directorio con wallpaper.json (o sin él).
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

-- hl falso: registra los comandos pasados a hl.exec_cmd
local exec_calls = {}
local hl = {
    exec_cmd = function(cmd) exec_calls[#exec_calls + 1] = cmd end,
}

local applied = settings.wallpaper(hl)
local case = os.getenv("SPEC_CASE") or "animated"

if case == "animated" then
    check("aplica 1 monitor animado", applied == 1 and #exec_calls == 1)
    local cmd = exec_calls[1] or ""
    check("comando usa el script wallpaper-swww.sh", cmd:find("wallpaper%-swww%.sh") ~= nil)
    check("pasa --output DP-2", cmd:find("%-%-output 'DP%-2'") ~= nil)
    check("pasa --fit contain", cmd:find("%-%-fit 'contain'") ~= nil)
    check("incluye la ruta del gif", cmd:find("Maiden%.gif") ~= nil)

elseif case == "static_only" then
    check("no aplica nada si ningún monitor es animado", applied == 0 and #exec_calls == 0)

elseif case == "mixed" then
    check("solo aplica el animado", applied == 1 and #exec_calls == 1)
    check("el comando es el del monitor animado", (exec_calls[1] or ""):find("DP%-2") ~= nil)

elseif case == "empty" then -- JSON ausente o corrupto
    check("sin aplicaciones", applied == 0 and #exec_calls == 0)

else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures > 0 then os.exit(1) end
print("OK")
