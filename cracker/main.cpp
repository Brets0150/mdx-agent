#include <QCoreApplication>
#include <QCommandLineParser>
#include <QDebug>

#include "keyspacethread.h"
#include "runthread.h"
using namespace std;

int main(int argc, char *argv[]){
    QCoreApplication a(argc, argv);

    QCoreApplication::setApplicationName("mdxfind-wrapper");
    QCoreApplication::setApplicationVersion("1.0");

    QCommandLineParser parser;
    parser.setApplicationDescription("MDXfind Wrapper for Hashtopolis - Hash Algorithm Identification and Cracking");
    parser.addHelpOption();
    parser.addVersionOption();
    parser.addPositionalArgument("action", QCoreApplication::translate("main", "Action to execute (keyspace or crack)"));

    // Allow unknown options to be silently ignored (for Hashtopolis compatibility)
    parser.setOptionsAfterPositionalArgumentsMode(QCommandLineParser::ParseAsOptions);

    QCommandLineOption maskOption(QStringList() << "m" << "mask",
           QCoreApplication::translate("main", "Use mask for attack"),
           QCoreApplication::translate("main", "mask"));
    parser.addOption(maskOption);

    QCommandLineOption wordlistOption(QStringList() << "w" << "wordlist",
           QCoreApplication::translate("main", "Use wordlist for attack"),
           QCoreApplication::translate("main", "wordlist"));
    parser.addOption(wordlistOption);

    QCommandLineOption hashlistOption(QStringList() << "a" << "attacked-hashlist",
           QCoreApplication::translate("main", "Hashlist to attack"),
           QCoreApplication::translate("main", "hashlist"));
    parser.addOption(hashlistOption);

    QCommandLineOption skipOption(QStringList() << "s" << "skip",
           QCoreApplication::translate("main", "Keyspace to skip at the beginning"),
           QCoreApplication::translate("main", "skip"));
    parser.addOption(skipOption);

    QCommandLineOption lengthOption(QStringList() << "l" << "length",
           QCoreApplication::translate("main", "Length of the keyspace to run"),
           QCoreApplication::translate("main", "length"));
    parser.addOption(lengthOption);

    QCommandLineOption timeoutOption(QStringList() << "timeout",
           QCoreApplication::translate("main", "Stop cracking process after fixed amount of time"),
           QCoreApplication::translate("main", "seconds"));
    parser.addOption(timeoutOption);

    QCommandLineOption hashTypeOption(QStringList() << "t" << "type",
           QCoreApplication::translate("main", "Hash types for MDXfind (e.g., 'ALL,!user,salt' or 'MD5,SHA1')"),
           QCoreApplication::translate("main", "types"));
    parser.addOption(hashTypeOption);

    QCommandLineOption iterationsOption(QStringList() << "i" << "iterations",
           QCoreApplication::translate("main", "Number of iterations for hash algorithms"),
           QCoreApplication::translate("main", "count"));
    parser.addOption(iterationsOption);

    // Process the actual command line arguments given by the user
    // Use parse() instead of process() to handle unknown options gracefully
    if(!parser.parse(QCoreApplication::arguments())){
        // Silently ignore parse errors (unknown options from Hashtopolis)
        // Only show error if it's not about unknown options
        QString errorText = parser.errorText();
        if(!errorText.contains("Unknown option") && !errorText.contains("Unknown options")){
            cerr << "Error: " << errorText.toStdString() << endl;
            return -1;
        }
    }

    const QStringList args = parser.positionalArguments();

    // Check if help or version was requested (already handled by addHelpOption/addVersionOption)
    if(args.isEmpty()){
        parser.showHelp();
        return 0;
    }

    QString action = args.at(0);

    //qDebug() << "Executing action: " + action;

    QThread *thread;
    if(action.compare("keyspace") == 0){
        int type = 0;
        QString value = "";
        if(parser.value(maskOption).length() > 0){
            type = 1;
            value = parser.value(maskOption);
        }
        else if(parser.value(wordlistOption).length() > 0){
            type = 2;
            value = parser.value(wordlistOption);
        }
        thread = new KeyspaceThread(type, value);
    }
    else if(action.compare("crack") == 0){
        long long int skip = parser.value(skipOption).toLong();
        long long int length = parser.value(lengthOption).toLong();
        int timeout = parser.value(timeoutOption).toInt();
        QString hashlist = parser.value(hashlistOption);
        QString hashType = parser.value(hashTypeOption);
        int iterations = parser.value(iterationsOption).toInt();

        // Default values from your bash script
        if(hashType.isEmpty()){
            hashType = "ALL,!user,salt";
        }
        if(iterations == 0){
            iterations = 10;
        }

        int type = 0;
        QString attack = "";
        if(parser.value(maskOption).length() > 0){
            type = 1;
            attack = parser.value(maskOption);
        }
        else if(parser.value(wordlistOption).length() > 0){
            type = 2;
            attack = parser.value(wordlistOption);
        }
        thread = new RunThread(type, attack, hashlist, skip, length, timeout, hashType, iterations);
    }
    else{
        cerr << "Invalid action!" << endl;
        return -1;
    }

    QObject::connect(thread, SIGNAL(finished()), &a, SLOT(quit()));
    thread->start();

    return a.exec();
}
