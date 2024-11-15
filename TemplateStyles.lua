local frame = mw.getCurrentFrame()
local args = {}

return function (stylesheet)
	args.src = stylesheet
	return frame:extensionTag("templatestyles", nil, args)
end