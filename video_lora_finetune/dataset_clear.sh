#如果是视频连续帧的打标，最好随机drop一些catiion：


percentage=30 ## drop百分比
directory="./images"  # 默认在当前目录执行，你可以修改为其他目录

# 获取所有的png文件
png_files=($(find "$directory" -maxdepth 1 -type f -name "*.png"))

# 计算需要删除的文件数量
num_files=${#png_files[@]}
num_to_delete=$((num_files * percentage / 100))

if [ $num_to_delete -eq 0 ]; then
    echo "No files to delete with the given percentage."
    exit 0
fi

# 随机选择要删除的文件
files_to_delete=($(shuf -n $num_to_delete -e "${png_files[@]}"))

# 删除选中的png文件和对应的txt文件
for png_file in "${files_to_delete[@]}"; do
    # 提取文件名（不包含扩展名）
    file_name=$(basename "$png_file" .png)
    
    # 构造对应的txt文件名
    txt_file="${file_name}.txt"
    
    # 删除文件
    rm "$directory/$png_file"
    rm "$directory/$txt_file"
    
    echo "Deleted: $png_file and $txt_file"
done

echo "Deletion completed."
