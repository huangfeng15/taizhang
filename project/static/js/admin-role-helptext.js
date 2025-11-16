(function () {
  "use strict";

  // 记录已经按业务自定义过文案的字段，避免被通用规则覆盖
  var customizedIds = {};

  function updateManyToManyHelp(fieldId, options) {
    if (!fieldId) {
      return;
    }

    // 左侧「可选」列表标题和说明
    var fromLabel = document.querySelector('label[for="' + fieldId + '_from"]');
    var fromHelp = document.querySelector(
      "#" + fieldId + "_from_title p.helptext"
    );

    if (fromLabel && options.availableLabel) {
      fromLabel.textContent = options.availableLabel;
    }
    if (fromHelp && options.helpText) {
      fromHelp.textContent = options.helpText;
    }

    // 右侧「已选」列表标题
    var toLabel = document.querySelector('label[for="' + fieldId + '_to"]');
    if (toLabel && options.chosenLabel) {
      toLabel.textContent = options.chosenLabel;
    }

    // 操作按钮文案
    var chooseAllBtn = document.getElementById(fieldId + "_add_all");
    var addBtn = document.getElementById(fieldId + "_add");
    var removeBtn = document.getElementById(fieldId + "_remove");

    if (chooseAllBtn && options.chooseAllText) {
      chooseAllBtn.textContent = options.chooseAllText;
    }
    if (addBtn && options.addText) {
      addBtn.textContent = options.addText;
    }
    if (removeBtn && options.removeText) {
      removeBtn.textContent = options.removeText;
    }

    customizedIds[fieldId] = true;
  }

  window.addEventListener("load", function () {
    // 角色定义页面：权限多选框（业务文案）
    updateManyToManyHelp("id_permissions", {
      availableLabel: "可选权限",
      helpText:
        "请从左侧列表中选择需要的权限，然后点击“添加所选”按钮，将其加入右侧的已选权限列表。",
      chosenLabel: "已选权限",
      chooseAllText: "全部添加",
      addText: "添加所选",
      removeText: "移除所选",
    });

    // 用户档案页面：角色多选框（业务文案）
    updateManyToManyHelp("id_roles", {
      availableLabel: "可选角色",
      helpText:
        "请从左侧列表中选择需要的角色，然后点击“添加所选”按钮，将其加入右侧的已选角色列表。",
      chosenLabel: "已选角色",
      chooseAllText: "全部添加",
      addText: "添加所选",
      removeText: "移除所选",
    });

    // 通用规则：统一后台所有 FilteredSelect 多选组件的中文文案
    var selects = document.querySelectorAll(
      "select.selectfilter, select.selectfilterstacked"
    );

    selects.forEach(function (el) {
      // 原生ID形如 id_permissions_from，这里去掉 _from 得到字段ID
      var id = el.id || "";
      var fieldId = id.endsWith("_from") ? id.slice(0, -5) : id;
      if (!fieldId || customizedIds[fieldId]) {
        return;
      }

      var fieldName =
        (el.dataset && el.dataset.fieldName) ||
        "项目"; // 兜底用一个中性词

      updateManyToManyHelp(fieldId, {
        availableLabel: "可选" + fieldName,
        helpText:
          "请从左侧列表中选择需要的" +
          fieldName +
          "，然后点击“添加所选”按钮，将其加入右侧的已选" +
          fieldName +
          "列表。",
        chosenLabel: "已选" + fieldName,
        chooseAllText: "全部添加",
        addText: "添加所选",
        removeText: "移除所选",
      });
    });
  });
})();
