-- Uso: SPEC_CASE=valid|disabled|transform|empty|corrupt lua tests/lua/monitors_spec.lua
-- HYPR_AJUSTES_DIR debe apuntar al directorio con monitors.json (o sin él).
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

-- hl falso: registra llamadas a hl.monitor y hl.config
local monitor_calls = {}
local config_calls = {}
local hl = {
    monitor = function(spec) monitor_calls[#monitor_calls + 1] = spec end,
    config  = function(cfg)  config_calls[#config_calls + 1] = cfg  end,
}

local registered = settings.monitors(hl)
local case = os.getenv("SPEC_CASE") or "valid"

if case == "valid" then
    check("registra 2 monitores", registered == 2 and #monitor_calls == 2)
    check("output del primer monitor", monitor_calls[1].output == "DP-1")
    check("modo del primer monitor", monitor_calls[1].mode == "3440x1440@144.00Hz")
    check("posición del primer monitor", monitor_calls[1].position == "0 0")
    check("scale del primer monitor", monitor_calls[1].scale == 1.0)
    check("transform del primer monitor", monitor_calls[1].transform == 0)
    check("disabled=false para enabled=true", monitor_calls[1].disabled == false)
    check("output del segundo monitor", monitor_calls[2].output == "DP-2")
    check("posición del segundo monitor", monitor_calls[2].position == "3440 0")

elseif case == "disabled" then
    check("registra el monitor", registered == 1 and #monitor_calls == 1)
    check("disabled=true para enabled=false", monitor_calls[1].disabled == true)

elseif case == "transform" then
    check("registra el monitor", registered == 1 and #monitor_calls == 1)
    check("transform=1 se pasa correctamente", monitor_calls[1].transform == 1)

elseif case == "empty" then -- JSON ausente o corrupto
    check("sin monitores registrados", registered == 0 and #monitor_calls == 0)

else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures > 0 then os.exit(1) end
print("OK")
