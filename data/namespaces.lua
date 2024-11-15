local data = {}

local gsub = string.gsub
local next = next
local ulower = require("Module:string utilities").lower

for _, namespace in next, mw.site.namespaces do
	local prefix = ulower((gsub(namespace.name, "_", " ")))
	data[prefix] = prefix
	for _, alias in next, namespace.aliases do
		data[ulower((gsub(alias, "_", " ")))] = prefix
	end
end

return data