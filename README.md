# QQ/TIM 历史版本归档

本仓库用于收集、整理和保存 QQ 与 TIM 的历史版本安装包，方便版本追溯或需要特定版本的场景。

## 内容来源

- QQ/TIM 官方页：用于后续获取新发布版本。
- 公开历史版本页面：用于补齐官方已经下架的旧版本。

## 文件组织

- `catalog/`：QQ 和 TIM 的机器可读版本索引。
- `checksums/`：Release 资产的 SHA-256 校验清单。
- `scripts/`：版本导入、下载、校验和 Release 自动化脚本。
- `site/`：静态下载页面。
- GitHub Releases：实际 APK 安装包和每次发布的说明。

每个版本至少记录：

- 产品和包名；
- `versionName` 与 `versionCode`；
- 原始文件名、文件大小和 SHA-256；
- 对应的 GitHub Release 和资产链接；
- 包元数据是否已经验证。

## Release 命名

Release tag 使用产品前缀和原始版本信息：

```text
qq-<versionName>-<versionCode>
tim-<versionName>-<versionCode>
```

如果没有可靠的 `versionCode`，使用 `unknown`。

## 校验与声明

下载或上传完成后计算 SHA-256。相同版本从不同来源取得时，优先通过哈希确认是否为同一文件。

该仓库用于历史归档。QQ、TIM 及其安装包的版权和发布权归腾讯所有；仓库不修改安装包内容，也不将第三方软件声明为本项目所有。