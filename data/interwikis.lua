local data = {}

local gsub = string.gsub
local next = next
local ulower = require("Module:string utilities").lower

for _, interwiki in next, mw.site.interwikiMap() do
	data[ulower((gsub(interwiki.prefix, "_", " ")))] =
		interwiki.isCurrentWiki and "current" or
		interwiki.isLocal and "local" or
		"external"
end

return data