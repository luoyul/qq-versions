# QQ 历史版本仓库

本仓库只保存 QQ Android 历史版本的索引、校验信息和 GitHub Release 记录。

## 内容

- `catalog/qq.json`：QQ 版本索引；
- `checksums/`：已验证文件的 SHA-256 清单；
- `scripts/`：历史版本导入和校验脚本；
- GitHub Releases：QQ APK 安装包。

Release tag 使用 `qq-<versionName>-<versionCode>` 格式。APK 不提交到 Git 仓库，实际文件只放在对应 Release 中。

这是 QQ/TIM 版本归档系统中的 QQ 数据仓库。静态索引页面位于 `qq-tim-archive-site` 仓库。
