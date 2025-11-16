(function () {
  "use strict";

  function updateManyToManyHelp(fieldId, options) {
    if (!fieldId) {
      return;
    }

    // 左侧「可选」列表标题和说明
    var fromLabel = document.querySelector('label[for="' + fieldId + '_from"]');
    var fromHelp = document.querySelector('#' + fieldId + '_from_title p.helptext');

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
    var chooseAllBtn = document.getElementById(fieldId + '_add_all');
    var addBtn = document.getElementById(fieldId + '_add');
    var removeBtn = document.getElementById(fieldId + '_remove');

    if (chooseAllBtn && options.chooseAllText) {
      chooseAllBtn.textContent = options.chooseAllText;
    }
    if (addBtn && options.addText) {
      addBtn.textContent = options.addText;
    }
    if (removeBtn && options.removeText) {
      removeBtn.textContent = options.removeText;
    }
  }

  window.addEventListener("load", function () {
    // 角色定义页面：权限多选框
    updateManyToManyHelp("id_permissions", {
      availableLabel: "可选权限",
      helpText:
        "请从左侧列表中选择需要的权限，然后点击“添加所选”按钮，将其加入右侧的已选权限列表。",
      chosenLabel: "已选权限",
      chooseAllText: "全部添加",
      addText: "添加所选",
      removeText: "移除所选",
    });

    // 用户档案页面：角色多选框
    updateManyToManyHelp("id_roles", {
      availableLabel: "可选角色",
      helpText:
        "请从左侧列表中选择需要的角色，然后点击“添加所选”按钮，将其加入右侧的已选角色列表。",
      chosenLabel: "已选角色",
      chooseAllText: "全部添加",
      addText: "添加所选",
      removeText: "移除所选",
    });
  });
})();