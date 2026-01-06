import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "RM.Styler",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "RMStyler") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                const categoryWidget = this.widgets.find((w) => w.name === "category");
                const styleWidget = this.widgets.find((w) => w.name === "style");

                if (!categoryWidget || !styleWidget) {
                    return r;
                }

                // Fetch data from the Python API
                const fetchData = async () => {
                    try {
                        const response = await api.fetchApi("/rm_styler/data");
                        const data = await response.json();
                        return data;
                    } catch (error) {
                        console.error("RMStyler: Error fetching style data", error);
                        return {};
                    }
                };

                // Logic to update the style widget options
                const updateStyles = (stylesMap, selectedCategory) => {
                    if (stylesMap && stylesMap[selectedCategory]) {
                        styleWidget.options.values = stylesMap[selectedCategory];
                        
                        // Default to first item if current selection is invalid
                        if (!stylesMap[selectedCategory].includes(styleWidget.value)) {
                            styleWidget.value = stylesMap[selectedCategory][0];
                        }
                    } else {
                        styleWidget.options.values = ["No Styles Found"];
                        styleWidget.value = "No Styles Found";
                    }
                };

                // Initialize
                fetchData().then((stylesMap) => {
                    // 1. Initial Update
                    updateStyles(stylesMap, categoryWidget.value);

                    // 2. Setup Callback for when Category changes
                    // We preserve existing callbacks if any
                    const originalCallback = categoryWidget.callback;
                    categoryWidget.callback = function (value) {
                        updateStyles(stylesMap, value);
                        if (originalCallback) {
                            return originalCallback.apply(this, arguments);
                        }
                    };
                });

                return r;
            };
        }
    },
});