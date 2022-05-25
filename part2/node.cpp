/*
 * Matthew Herdzik
 * csci 499
 * IPFS Node Networking
 * Build: g++ node.cpp -o n
 * Execute:
 *      ./n <SRC PORT>
 *      ./n <SRC PORT> <DEST PORT> create <FILEHASH>
 */

#include <iostream>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <netdb.h>
#include <arpa/inet.h>

#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "ipfs_hlpr.h"


/* src port, dst port, file arg, filehash, */
int main(int argc, char** argv){
    bool errchk = false, receiver = false;
    if (argc < 2) {
        std::cerr << "Invalid number of arguments.\n";
        return -1;
    }
    else if (argc == 2) receiver = true;

    /* Set Timer */
    int timer_s = 60;
    struct timeval tv;
    tv.tv_usec = 0;
    tv.tv_sec = timer_s;

    if(receiver){
        /* Collect Source Port from command line argument */
        std::string str_srcprt(argv[1]);
        int SRCPORT = stoi(str_srcprt);
        /* Start of Socket Initialization */
        int _src = SRCPORT;
        int listening = socket(AF_INET, SOCK_STREAM, 0);
        if (listening == -1) return -2;
        sockaddr_in hint;
        hint.sin_family = AF_INET;
        hint.sin_port = htons(_src);
        inet_pton(AF_INET, "0.0.0.0", &hint.sin_addr);
        if (bind(listening, (sockaddr * ) & hint, sizeof(hint)) == -1) return -2;
        if (listen(listening, SOMAXCONN) == -1) return -2;
        sockaddr_in client;
        socklen_t client_size = sizeof(client);
        char host[NI_MAXHOST];
        char svc[NI_MAXSERV];
        int client_socket = accept(listening, (sockaddr * ) & client, &client_size);
        if (client_socket == -1) return -2;
        close(listening);
        setsockopt(client_socket, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));
        memset(host, 0, NI_MAXHOST);
        memset(svc, 0, NI_MAXSERV);
        int result = getnameinfo((sockaddr * ) & client, sizeof(client), host, NI_MAXHOST, svc, NI_MAXSERV, 0);
        inet_ntop(AF_INET, &client.sin_addr, host, NI_MAXHOST);
        std::cout << host << " Connected on: " << ntohs(client.sin_port) << std::endl;
        int _dst = int(ntohs(client.sin_port));
        /* End of Socket Initialization. */
        
        std::vector<std::string> in_file;
        std::string filearg, filehash, filename, msg_rcvd, checklen;
        bool lstn = true, hsk = false, fin = false, syn = false, ack =false;
        char* buf;
        buf = new char[1024];
        int bytes_rcvd, ipfs_prtcl;

        while(lstn){
            /* loop until handshake successful or rst fail */
            while(!hsk){
                bytes_rcvd = recv(client_socket, buf, 1024, 0);
                if (bytes_rcvd > 0){
                    std::cout << "Error \n";
                }
                msg_rcvd = std::string(buf);
                memset(buf, 0, 1024);
                if (!syn){
                    if(before_colon(msg_rcvd) == "syn"){
                        syn = true;
                        str_char_convert(buf, "syn ack: , ");
                        send(client_socket, buf, 1024, 0);
                        memset(buf, 0, 1024);
                    }
                    else{
                        str_char_convert(buf, "error:syn, ");
                        send(client_socket, buf, 1024, 0);
                        memset(buf, 0, 1024);
                    }
                }
                else if (!ack){
                    /*When sender acknowledges syn-ack, will give filehash and filearg*/
                    if(before_colon(msg_rcvd) == "ack"){
                        ipfs_prtcl = file_protocol(after_colon(before_comma(msg_rcvd)));
                        filehash = (after_comma(msg_rcvd);
                        str_char_convert(buf, "ack: , ");
                        send(client_socket, buf, 1024, 0);
                        memset(buf, 0, 1024);
                        hsk = true;
                    }
                    else{
                        syn = false;
                    }
                }
                else{
                    str_char_convert(buf, ("rst: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
            }
            /*Sender gives block portions until fin is sent*/
            while(!fin){
                bytes_rcvd = recv(client_socket, buf, 1024, 0);
                msg_rcvd = std::string(buf);
                memset(buf, 0, 1024);
                /*error sent if checklen not successful*/
                if (before_colon(msg_rcvd) == "error"){
                    in_file.pop_back();
                    str_char_convert(buf, ("ready: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
                else if (before_colon(msg_rcvd) == "more") {
                    in_file.push_back(after_comma(msg_rcvd));
                    checklen = std::to_string(msg_rcvd.length());
                    str_char_convert(buf, ("ack:" + checklen + ", "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
                else if (before_colon(msg_rcvd) == "fin"){
                    str_char_convert(buf, ("fin: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                    fin = true;
                }
                else{
                    str_char_convert(buf, ("rst: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                    fin = true;
                }
            }
            close(client_socket);
        }
        /*print strings into file*/
        if (in_file.size() > 0){
            std::string full_file = "";
            for (const auto& x: in_file) {
                full_file += x;
            }
            /*Name file after hash*/
            std::ofstream outfile(filehash+".txt");
            outfile << full_file;
            outfile.close();
        }
    }
    else{
        /*Sender portion of node activated*/

        std::string str_dstprt(argv[2]);
        int DESTPORT = stoi(str_dstprt);
        std::string filearg(argv[3]);
        std::string filehash(argv[4]);
        
        /* Start of Socket Initialization. */
        int port = DESTPORT;
        std::string ip_addr = "127.0.0.1";
        int client_socket = socket(AF_INET, SOCK_STREAM, 0);
        if (client_socket == -1) return -1;
        sockaddr_in hint;
        hint.sin_family = AF_INET;
        hint.sin_port = htons(port);
        inet_pton(AF_INET, ip_addr.c_str(), &hint.sin_addr);
        int connectRes = connect(client_socket, (sockaddr*)&hint, sizeof(hint));
        if (connectRes == -1) return -1;
        /* End of Socket Initialization */
        if (errchk) std::cout << "send socket init \n";

        char* buf;
        buf = new char[1024];

        bool lstn = true, hsk = false, sendfile = false, first = true,fl_first = true;
        std::string msg_rcvd, output, checklen;

        int bytes_rcvd;
        //deprecated, used to cut file into N/windowsize strings: int ongoing = 0, windowsize = 50;

        std::ifstream file(filehash+".txt");
        if (file.fail()) {
            std::cerr << "Error: Failed to load file! " << std::endl;
            exit(1);
        }

        while(lstn){
            while(!hsk){ /*handshale*/
                if (first) {
                    str_char_convert(buf, ("syn: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                    first = false;
                }
                
                bytes_rcvd = recv(client_socket, buf, 1024, 0);
                msg_rcvd = std::string(buf);
                memset(buf, 0, 1024);

                if(before_colon(msg_rcvd) == "syn ack"){
                    str_char_convert(buf, ("ack:create,"+filehash));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                    hsk = true;
                }
                else if (before_colon(msg_rcvd) == "error") {
                    str_char_convert(buf, ("syn: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
                else {
                    str_char_convert(buf, ("syn: , "));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
            }
            while(!sendfile){
                /*Send block partitions line by line*/
                if(fl_first){
                    //output = file.substr(ongoing, windowsize);
                    std::getline(file, output);
                    str_char_convert(buf, ("more: ,"+output));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                    fl_first = false;
                }
                checklen = std::to_string(output.length());
                bytes_rcvd = recv(client_socket, buf, 1024, 0);
                msg_rcvd = std::string(buf);
                memset(buf, 0, 1024);
                if (before_comma(after_colon(msg_rcvd))==checklen){
                    //ongoing += windowsize;
                    //output = file.substr(ongoing, windowsize);
                    if(!std::getline(file, output)){
                        sendfile = true;
                    }
                    else{
                        str_char_convert(buf, ("more: ,"+output));
                        send(client_socket, buf, 1024, 0);
                        memset(buf, 0, 1024);
                    }
                }
                else{
                    str_char_convert(buf, ("error: ,"+output));
                    send(client_socket, buf, 1024, 0);
                    memset(buf, 0, 1024);
                }
                str_char_convert(buf, ("fin:fin,fin"));
                send(client_socket, buf, 1024, 0);
                memset(buf, 0, 1024);
            }
            close(client_socket);
            return 1;
        }
    }
}