#!/usr/bin/env bash

repository="$1"
directory="$2"

# проверяем репу
regex="^(https:\/\/github\.com\/([a-z0-9_-]+)\/vas3k\.club\/tree\/([^$]+)|([a-z0-9_]+):([^$]+))$"

if [[ ! $repository =~ $regex ]]; then
    echo "usage: clone-fork.sh \$repository \$directory"
    echo ""
    echo "repository -- full link to fork or fork name"
    echo "directory -- local directory to clone (default is \$developer/\$branch)"
    echo ""
    echo "samples:"
    echo "./clone-fork.sh trin4ik:feature/import-posts-to-dev ./"
    echo "./clone-fork.sh https://github.com/trin4ik/vas3k.club/tree/feature/import-posts-to-dev"
    exit
fi

developer=${BASH_REMATCH[2]}
if [[ -z "$developer" ]]; then
    developer=${BASH_REMATCH[4]}
fi

branch=${BASH_REMATCH[3]}
if [[ -z "$branch" ]]; then
    branch=${BASH_REMATCH[5]}
fi

if [[ $(curl -s -I -o /dev/null -w "%{http_code}" https://github.com/${developer}/vas3k.club/tree/${branch}) != "200" ]]; then
    echo "error: repository does not exist"
    exit
fi

if [[ -z $directory ]]; then
    directory="${developer}/${branch}"
fi

echo "developer: ${developer}"
echo "branch: ${branch}"

echo "create directory"
mkdir -p ${directory}

# клонируем репу
echo "cloning repository..."
git clone --branch ${branch} --single-branch https://github.com/${developer}/vas3k.club ${directory}

# меняем docker-compose
echo "change docker-compose.yml"
file="$(pwd)/${directory}/docker-compose.yml"
default_name="vas3kclub"
fork="${developer}/${branch}"
postfix=$(echo "$fork" | sed -r 's/[\/-]/_/g')
exists_name=$(grep -e '^name:' "$file" | awk '{ gsub(/"/, "", $2); print $2 }')

# создаём или меняем имя проекта
if [[ $exists_name ]]; then
    sed -i -e "s/^name:.*/name: \"${exists_name}_${postfix}\"/g" $file
else
    sed -i "1s/^/name: \"${default_name}_${postfix}\"\n/" $file
fi

# меняем `container_name`
while IFS= read -r line
do
    if [[ $line =~ ^([[:space:]]*)container_name:\ [^\n]+ ]]; then
        new_line="${BASH_REMATCH[1]}$(echo "$line" | awk -v postfix="$postfix" '{ gsub(/"/, "", $2); print $1" "$2"_"postfix }')"
        sed -i "s@${line}@${new_line}@" $file
    fi
done < $file

echo "done"
