# 1. git 基本使用

在 .gitignore 文件中，每一行代表一个匹配规则，可以使用通配符来匹配多个文件或文件夹。
例如：
+ 忽略单个文件: database.conf
+ 忽略整个文件夹: node_modules/
+ 忽略所有 .log 文件: *.log
+ 忽略特定文件夹下的所有文件: build/*
+ 更多 .gitignore 语法，可以参考 GitHub 的官方文档。


# 2. 提交更改:

```
git add .gitignore
git commit -m "Update .gitignore"
```
# 3. 推送更改到 GitHub:
```
git push origin <branch-name>
```