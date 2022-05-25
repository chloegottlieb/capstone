
#ifndef IPFS_SOCK_IPFS_HLPR_H
#define IPFS_SOCK_IPFS_HLPR_H

#include <iostream>

int file_protocol (std::string filearg){
    if (filearg == "create") return 1;
    if (filearg == "delete") return 9;
    else return 0;
}

std::string before_comma( const std::string & input ){
    int i{0};
    while(input.substr(i,1) != "," && i < input.length())
        i++;
    return input.substr(0,i);
}
std::string after_comma( const std::string & input ){
    int i{0};
    while(input.substr(i,1) != "," && i < input.length())
        i++;
    return input.substr(i+1, input.length()-i);
}
std::string before_colon( const std::string & input ){
    int i{0};
    while(input.substr(i,1) != ":" && i < input.length())
        i++;
    return input.substr(0,i);
}
std::string after_colon( const std::string & input ){
    int i{0};
    while(input.substr(i,1) != ":" && i < input.length())
        i++;
    return input.substr(i+1, input.length()-i);
}
void str_char_convert(char* arr, const std::string & input){
    const char *tmp = input.c_str();
    for (int i{0}; i < input.length(); i++){
        arr[i] = tmp[i];
    }
}

#endif //IPFS_SOCK_IPFS_HLPR_H
