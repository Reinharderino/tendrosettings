-- Uso: SPEC_CASE=valid|skip_no_monitor|empty lua tests/lua/workspaces_spec.lua
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

local rule_calls = {}
local hl = {
    workspace_rule = function(spec) rule_calls[#rule_calls + 1] = spec end,
}

local registered = settings.workspaces(hl)
local case = os.getenv("SPEC_CASE") or "valid"

if case == "valid" then
    check("registra 2 reglas", registered == 2 and #rule_calls == 2)
    check("workspace es string", rule_calls[1].workspace == "1")
    check("monitor correcto", rule_calls[1].monitor == "DP-1")
    check("persistent true", rule_calls[1].persistent == true)
    check("persistent false por defecto", rule_calls[2].persistent == false)
elseif case == "skip_no_monitor" then
    check("omite workspace sin monitor", registered == 0 and #rule_calls == 0)
elseif case == "empty" then
    check("sin reglas", registered == 0 and #rule_calls == 0)
else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures > 0 then os.exit(1) end
print("OK")
