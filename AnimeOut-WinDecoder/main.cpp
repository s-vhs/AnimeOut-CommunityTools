#include "framework.h"
#include "AnimeOut-WinDecoder.h"
#include <shobjidl.h>
#include <fstream>
#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <windows.h>
#include <algorithm>
#include <memory>
#include <regex>
#include <stdexcept>
#include <locale>
#include <codecvt>
#include <shellapi.h>

#define MAX_LOADSTRING 100
#define DECODE_FLASH_TIMER_ID 1001
#define ENCODE_FLASH_TIMER_ID 1002

int decodeFlashCount = 0;
int encodeFlashCount = 0;
const int maxFlashes = 6; // Number of flashes

// Global Variables:
HINSTANCE hInst;                                // Current Instance
WCHAR szTitle[MAX_LOADSTRING];                  // Window title text
WCHAR szWindowClass[MAX_LOADSTRING];            // Main window class name.

// Forward declarations of functions included in this code module:
ATOM                RegisterWindowClass(HINSTANCE hInstance);
BOOL                InitializeInstance(HINSTANCE, int);
LRESULT CALLBACK    WindowProc(HWND, UINT, WPARAM, LPARAM);
INT_PTR CALLBACK    AboutDialogProc(HWND, UINT, WPARAM, LPARAM);

//void ShowFolderSelectionDialog();
void ProcessDirectory(const std::wstring& folderPath, bool isRecursive, bool renameFolders, bool decode);

// Main function:
int APIENTRY wWinMain(_In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR    lpCmdLine,
    _In_ int       nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    // Initialize global strings
    LoadStringW(hInstance, IDS_APP_TITLE, szTitle, MAX_LOADSTRING);
    LoadStringW(hInstance, IDC_ANIMEOUTWINDECODER, szWindowClass, MAX_LOADSTRING);
    RegisterWindowClass(hInstance);

    // Perform application initialization:
    if (!InitializeInstance(hInstance, nCmdShow))
    {
        return FALSE;
    }

    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_ANIMEOUTWINDECODER));

    MSG msg;

    // Main message loop:
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        if (!TranslateAccelerator(msg.hwnd, hAccelTable, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    return (int)msg.wParam;
}

// Timer callback function
void CALLBACK FlashButtonProc(HWND hWnd, UINT message, UINT idTimer, DWORD dwTime) {
    static HWND hButton = NULL;
    static int* flashCount = NULL;
    static UINT timerId = 0;

    if (idTimer == DECODE_FLASH_TIMER_ID) {
        hButton = GetDlgItem(hWnd, 4); // Decode button
        flashCount = &decodeFlashCount;
        timerId = DECODE_FLASH_TIMER_ID;
    }
    else if (idTimer == ENCODE_FLASH_TIMER_ID) {
        hButton = GetDlgItem(hWnd, 5); // Encode button
        flashCount = &encodeFlashCount;
        timerId = ENCODE_FLASH_TIMER_ID;
    }

    if (hButton) {
        if (IsWindowVisible(hButton)) {
            ShowWindow(hButton, SW_HIDE);
        }
        else {
            ShowWindow(hButton, SW_SHOW);
        }

        (*flashCount)++;
        if (*flashCount >= maxFlashes) {
            KillTimer(hWnd, timerId);
            ShowWindow(hButton, SW_SHOW); // Ensure button is visible after flashing
        }
    }
}

// Function to get the Temp directory path
std::wstring GetTempDirectory() {
    wchar_t tempPath[MAX_PATH];
    GetTempPathW(MAX_PATH, tempPath);
    return std::wstring(tempPath);
}

// Function to save the folder path to a file in the Temp directory
void SaveFolderPath(const std::wstring& path) {
    std::wstring filePath = GetTempDirectory() + L"FolderPath.txt";
    std::wofstream file(filePath);
    if (file.is_open()) {
        file << path;
        file.close();
    }
    else {
        MessageBoxW(NULL, L"Error saving the folder path.", L"Error", MB_OK | MB_ICONERROR);
    }
}

// Function to save checkbox states to a file in the Temp directory
void SaveCheckboxStates(bool isRecursive, bool renameFolders) {
    std::wstring filePath = GetTempDirectory() + L"CheckboxStates.txt";
    std::wofstream file(filePath);
    if (file.is_open()) {
        file << isRecursive << L"\n" << renameFolders;
        file.close();
    }
    else {
        MessageBoxW(NULL, L"Error saving the checkbox states.", L"Error", MB_OK | MB_ICONERROR);
    }
}

// Function to load checkbox states from a file in the Temp directory
void LoadCheckboxStates(bool& isRecursive, bool& renameFolders) {
    std::wstring filePath = GetTempDirectory() + L"CheckboxStates.txt";
    std::wifstream file(filePath);
    if (file.is_open()) {
        file >> isRecursive;
        file >> renameFolders;
        file.close();
    }
    else {
        isRecursive = false;
        renameFolders = false;
    }
}

// Function to check if a value is Base64 encoded
bool IsBase64(const std::wstring& value) {
    // Regular expression to check Base64 characters
    std::wregex base64Pattern(L"^[A-Za-z0-9+/=]*$");
    if (!std::regex_match(value.begin(), value.end(), base64Pattern)) {
        return false;
    }

    // Decode the Base64 string
    try {
        // Base64 decoding table
        static const std::vector<unsigned char> decodingTable = {
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 00-15
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 16-31
            64, 62, 64, 64, 64, 64, 64, 63, 64, 64, 64, 64, 64, 64, 64, 64, // 32-47
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 48-63
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 64-79
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 80-95
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 96-111
            64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64  // 112-127
        };

        // Base64 decoding function
        auto base64Decode = [](const std::wstring& encoded) -> std::string {
            std::string decoded;
            size_t length = encoded.length();
            size_t padding = 0;

            if (encoded[length - 1] == L'=') padding++;
            if (encoded[length - 2] == L'=') padding++;

            size_t decodedLength = (length * 3) / 4 - padding;
            decoded.resize(decodedLength);

            size_t j = 0;
            uint32_t temp = 0;
            size_t tempLength = 0;

            for (size_t i = 0; i < length; i++) {
                uint8_t c = (encoded[i] >= L'A' && encoded[i] <= L'Z') ? (encoded[i] - L'A') :
                    (encoded[i] >= L'a' && encoded[i] <= L'z') ? (encoded[i] - L'a' + 26) :
                    (encoded[i] >= L'0' && encoded[i] <= L'9') ? (encoded[i] - L'0' + 52) :
                    (encoded[i] == L'+') ? 62 :
                    (encoded[i] == L'/') ? 63 : 64;

                if (c == 64) continue; // Invalid character

                temp = (temp << 6) | c;
                tempLength += 6;

                if (tempLength >= 8) {
                    tempLength -= 8;
                    decoded[j++] = static_cast<char>((temp >> tempLength) & 0xFF);
                }
            }

            return decoded;
            };

        // Check if the decoding does not throw an exception
        std::string decodedData = base64Decode(value);
        return !decodedData.empty(); // If decoding was successful, return true
    }
    catch (...) {
        return false;
    }
}

std::wstring Base64Decode(const std::wstring& encoded) {
    // Base64 decoding table
    static const std::vector<unsigned char> decodingTable = {
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 00-15
        64, 62, 64, 64, 64, 64, 64, 63, 64, 64, 64, 64, 64, 64, 64, 64, // 16-31
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 32-47
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 48-63
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 64-79
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 80-95
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, // 96-111
        64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64  // 112-127
    };

    std::wstring decoded;
    size_t length = encoded.length();
    size_t padding = 0;

    // Handle padding
    if (encoded[length - 1] == L'=') padding++;
    if (encoded[length - 2] == L'=') padding++;

    // Calculate decoded length
    size_t decodedLength = (length * 3) / 4 - padding;
    decoded.resize(decodedLength);

    size_t j = 0;
    uint32_t temp = 0;
    size_t tempLength = 0;

    for (size_t i = 0; i < length; i++) {
        uint8_t c = (encoded[i] >= L'A' && encoded[i] <= L'Z') ? (encoded[i] - L'A') :
            (encoded[i] >= L'a' && encoded[i] <= L'z') ? (encoded[i] - L'a' + 26) :
            (encoded[i] >= L'0' && encoded[i] <= L'9') ? (encoded[i] - L'0' + 52) :
            (encoded[i] == L'+') ? 62 :
            (encoded[i] == L'/') ? 63 : 64;

        if (c == 64) continue; // Invalid character

        temp = (temp << 6) | c;
        tempLength += 6;

        if (tempLength >= 8) {
            tempLength -= 8;
            decoded[j++] = static_cast<wchar_t>((temp >> tempLength) & 0xFF);
        }
    }

    return decoded;
}

std::wstring Base64Encode(const std::wstring& data) {
    // Base64 encoding table
    static const wchar_t encodingTable[] = L"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    size_t length = data.length();
    size_t encodedLength = 4 * ((length + 2) / 3); // Calculate encoded length
    std::wstring encoded;
    encoded.reserve(encodedLength);

    uint32_t temp = 0;
    size_t tempLength = 0;

    for (size_t i = 0; i < length; ++i) {
        temp = (temp << 8) | data[i];
        tempLength += 8;

        while (tempLength >= 6) {
            tempLength -= 6;
            encoded.push_back(encodingTable[(temp >> tempLength) & 0x3F]);
        }
    }

    if (tempLength > 0) {
        temp <<= (6 - tempLength);
        encoded.push_back(encodingTable[temp & 0x3F]);
    }

    while (encoded.length() % 4 != 0) {
        encoded.push_back(L'=');
    }

    return encoded;
}


// Function to process the directory
void ProcessDirectory(const std::wstring& folderPath, bool isRecursive, bool renameFolders, bool decode) {
    std::wstring searchPath = folderPath + L"\\*";
    WIN32_FIND_DATA findFileData;
    HANDLE hFind = FindFirstFile(searchPath.c_str(), &findFileData);

    if (hFind == INVALID_HANDLE_VALUE) {
        MessageBoxW(NULL, L"Error accessing directory.", L"Error", MB_OK | MB_ICONERROR);
        return;
    }

    std::vector<std::wstring> subDirectories;

    do {
        std::wstring filePath = folderPath + L"\\" + findFileData.cFileName;
        bool isDirectory = (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;

        if (isDirectory) {
            // It's a directory
            if (wcscmp(findFileData.cFileName, L".") != 0 && wcscmp(findFileData.cFileName, L"..") != 0) {
                // Avoid processing the current and parent directory
                subDirectories.push_back(filePath);
            }
        }
        else {
            // It's a file
            std::wstring fileName = findFileData.cFileName;
            std::wstring name = fileName.substr(0, fileName.find_last_of(L"."));
            std::wstring extension = fileName.substr(fileName.find_last_of(L"."));

            if (decode && IsBase64(name)) {
                // Decode Base64 name
                std::wstring decodedName = Base64Decode(name);
                std::wstring newFileName = decodedName + extension;
                std::wstring newFilePath = folderPath + L"\\" + newFileName;

                if (MoveFile(filePath.c_str(), newFilePath.c_str())) {
                    // MessageBoxW(NULL, (L"Decoded and renamed file: " + fileName + L" -> " + newFileName).c_str(), L"Info", MB_OK);
                }
                else {
                    // MessageBoxW(NULL, (L"Failed to rename file: " + fileName).c_str(), L"Error", MB_OK | MB_ICONERROR);
                }
            }
            else if (!decode) {
                // Encode the file name
                if (!IsBase64(name)) {
                    std::wstring encodedName = Base64Encode(name);
                    std::wstring newFileName = encodedName + extension;
                    std::wstring newFilePath = folderPath + L"\\" + newFileName;

                    if (MoveFile(filePath.c_str(), newFilePath.c_str())) {
                        // MessageBoxW(NULL, (L"Encoded and renamed file: " + fileName + L" -> " + newFileName).c_str(), L"Info", MB_OK);
                    }
                    else {
                        // MessageBoxW(NULL, (L"Failed to rename file: " + fileName).c_str(), L"Error", MB_OK | MB_ICONERROR);
                    }
                }
            }
        }
    } while (FindNextFile(hFind, &findFileData) != 0);

    FindClose(hFind);

    for (const auto& subDirectory : subDirectories) {
        if (isRecursive) {
            ProcessDirectory(subDirectory, isRecursive, renameFolders, decode);
        }

        if (renameFolders) {
            std::wstring folderName = subDirectory.substr(subDirectory.find_last_of(L"\\") + 1);

            if (decode && IsBase64(folderName)) {
                // Decode Base64 name
                std::wstring decodedName = Base64Decode(folderName);
                std::wstring newFolderPath = folderPath + L"\\" + decodedName;

                if (MoveFile(subDirectory.c_str(), newFolderPath.c_str())) {
                    // MessageBoxW(NULL, (L"Decoded and renamed folder: " + folderName + L" -> " + decodedName).c_str(), L"Info", MB_OK);
                }
                else {
                    // MessageBoxW(NULL, (L"Failed to rename folder: " + folderName).c_str(), L"Error", MB_OK | MB_ICONERROR);
                }
            }
            else if (!decode) {
                // Encode the directory name
                if (!IsBase64(folderName)) {
                    std::wstring encodedName = Base64Encode(folderName);
                    std::wstring newFolderPath = folderPath + L"\\" + encodedName;

                    if (MoveFile(subDirectory.c_str(), newFolderPath.c_str())) {
                        // MessageBoxW(NULL, (L"Encoded and renamed folder: " + folderName + L" -> " + encodedName).c_str(), L"Info", MB_OK);
                    }
                    else {
                        // MessageBoxW(NULL, (L"Failed to rename folder: " + folderName).c_str(), L"Error", MB_OK | MB_ICONERROR);
                    }
                }
            }
        }
    }
}

//
//  FUNCTION: RegisterWindowClass()
//
//  PURPOSE: Registers the window class.
//
ATOM RegisterWindowClass(HINSTANCE hInstance)
{
    WNDCLASSEXW wcex;

    wcex.cbSize = sizeof(WNDCLASSEX);

    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WindowProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_ANIMEOUTWINDECODER));
    wcex.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = MAKEINTRESOURCEW(IDI_ANIMEOUTWINDECODER);
    wcex.lpszClassName = szWindowClass;
    wcex.hIconSm = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));

    return RegisterClassExW(&wcex);
}

//
//   FUNCTION: InitializeInstance(HINSTANCE, int)
//
//   PURPOSE: Stores the instance handle and creates the main window.
//
BOOL InitializeInstance(HINSTANCE hInstance, int nCmdShow)
{
    hInst = hInstance; // Store instance handle in global variable

    // Set window title
    lstrcpyW(szTitle, L"AO-WinDecoder 1.0");

    HWND hWnd = CreateWindowW(szWindowClass, szTitle, WS_OVERLAPPED | WS_SYSMENU | WS_CAPTION,
        CW_USEDEFAULT, 0, 200, 245, nullptr, nullptr, hInstance, nullptr);

    if (!hWnd)
    {
        return FALSE;
    }

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    // Create "Select Folder" button
    CreateWindow(
        L"BUTTON",
        L"Select Folder",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,
        0,   // x-position
        0,   // y-position
        185, // Width
        30,  // Height
        hWnd,
        (HMENU)1,
        hInstance,
        NULL
    );

    // Create "Recursive" checkbox
    HWND hRecursiveCheckBox = CreateWindow(
        L"BUTTON",
        L"Recursive",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_CHECKBOX | BS_AUTOCHECKBOX,
        5,   // x-position
        30,  // y-position
        180, // Width
        30,  // Height
        hWnd,
        (HMENU)2,
        hInstance,
        NULL
    );

    // Create "Folders" checkbox
    HWND hFoldersCheckBox = CreateWindow(
        L"BUTTON",
        L"Folders",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_CHECKBOX | BS_AUTOCHECKBOX,
        5,   // x-position
        60,  // y-position
        180, // Width
        30,  // Height
        hWnd,
        (HMENU)3,
        hInstance,
        NULL
    );

    // Load and set checkbox states
    bool isRecursive = false, renameFolders = false;
    LoadCheckboxStates(isRecursive, renameFolders);
    SendMessage(hRecursiveCheckBox, BM_SETCHECK, isRecursive ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessage(hFoldersCheckBox, BM_SETCHECK, renameFolders ? BST_CHECKED : BST_UNCHECKED, 0);

    // Create "Decode!" button
    CreateWindow(
        L"BUTTON",
        L"Decode!",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,
        0,   // x-position
        90,  // y-position
        185, // Width
        30,  // Height
        hWnd,
        (HMENU)4, // Button ID
        hInstance,
        NULL
    );

    // Create "Encode!" button
    CreateWindow(
        L"BUTTON",
        L"Encode!",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,
        0,   // x-position
        120,  // y-position
        185, // Width
        30,  // Height
        hWnd,
        (HMENU)5, // Button ID
        hInstance,
        NULL
    );

    // Create horizontal line (using static control with SS_ETCHEDHORZ style)
    CreateWindow(
        L"STATIC",
        NULL,
        WS_CHILD | WS_VISIBLE | SS_ETCHEDHORZ,
        0,   // x-position
        155, // y-position (below the Decode button)
        185, // Width
        2,   // Height of the line
        hWnd,
        NULL,
        hInstance,
        NULL
    );

    // Create "Visit GitHub" button
    CreateWindow(
        L"BUTTON",
        L"Visit GitHub",
        WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,
        0,   // x-position
        160, // y-position (below the Decode button)
        185, // Width
        30,  // Height
        hWnd,
        (HMENU)6, // New Button ID
        hInstance,
        NULL
    );

    // Create plaintext below the "Open Google" button
    CreateWindow(
        L"STATIC",
        L"Discord: @ForsakenMaiden",
        WS_CHILD | WS_VISIBLE | SS_LEFT,
        0,   // x-position
        190, // y-position (below the Open Google button)
        185, // Width
        15,  // Height
        hWnd,
        NULL,
        hInstance,
        NULL
    );

    return TRUE;
}

//
//  FUNCTION: WindowProc(HWND, UINT, WPARAM, LPARAM)
//
//  PURPOSE: Processes messages for the main window.
//
LRESULT CALLBACK WindowProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_COMMAND:
    {
        int wmId = LOWORD(wParam);
        // Analyze menu selections:
        switch (wmId)
        {
        case 1: // Select Folder button
        {
            IFileDialog* pfd = NULL;
            HRESULT hr = CoCreateInstance(CLSID_FileOpenDialog, NULL, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&pfd));
            if (SUCCEEDED(hr))
            {
                hr = pfd->SetOptions(FOS_PICKFOLDERS);
                if (SUCCEEDED(hr))
                {
                    hr = pfd->Show(hWnd);
                    if (SUCCEEDED(hr))
                    {
                        IShellItem* pItem;
                        hr = pfd->GetResult(&pItem);
                        if (SUCCEEDED(hr))
                        {
                            PWSTR pszFolderPath = NULL;
                            hr = pItem->GetDisplayName(SIGDN_FILESYSPATH, &pszFolderPath);
                            if (SUCCEEDED(hr))
                            {
                                // Save folder path
                                SaveFolderPath(pszFolderPath);
                                CoTaskMemFree(pszFolderPath);
                            }
                            pItem->Release();
                        }
                    }
                }
                pfd->Release();
            }
            break;
        }
        case 2: // Recursive checkbox
        {
            HWND hCheckBox = GetDlgItem(hWnd, 2);
            bool isRecursive = (SendMessage(hCheckBox, BM_GETCHECK, 0, 0) == BST_CHECKED);
            // Store or use the recursive flag as needed
            // Save the flag or use it directly in the decode process
            break;
        }
        case 3: // Folders checkbox
        {
            HWND hCheckBox = GetDlgItem(hWnd, 3);
            bool renameFolders = (SendMessage(hCheckBox, BM_GETCHECK, 0, 0) == BST_CHECKED);
            // Store or use the folders flag as needed
            // Save the flag or use it directly in the decode process
            break;
        }
        case 4: // Decode! button
        {
            HWND hCheckBox = GetDlgItem(hWnd, 2);
            bool isRecursive = (SendMessage(hCheckBox, BM_GETCHECK, 0, 0) == BST_CHECKED);
            HWND hCheckBox2 = GetDlgItem(hWnd, 3);
            bool renameFolders = (SendMessage(hCheckBox2, BM_GETCHECK, 0, 0) == BST_CHECKED);

            SaveCheckboxStates(isRecursive, renameFolders);

            std::wifstream file(GetTempDirectory() + L"FolderPath.txt");
            if (file.is_open()) {
                std::wstring folderPath;
                std::getline(file, folderPath);
                file.close();

                ProcessDirectory(folderPath, isRecursive, renameFolders, true);

                KillTimer(hWnd, ENCODE_FLASH_TIMER_ID); // Ensure no conflicting timer

                decodeFlashCount = 0;
                SetTimer(hWnd, DECODE_FLASH_TIMER_ID, 100, (TIMERPROC)FlashButtonProc);
                ShowWindow(GetDlgItem(hWnd, 4), SW_SHOW);
            }
            else {
                MessageBoxW(NULL, L"Folder path file not found.", L"Error", MB_OK | MB_ICONERROR);
            }
            break;
        }
        case 5: // Encode! button
        {
            HWND hCheckBox = GetDlgItem(hWnd, 2);
            bool isRecursive = (SendMessage(hCheckBox, BM_GETCHECK, 0, 0) == BST_CHECKED);
            HWND hCheckBox2 = GetDlgItem(hWnd, 3);
            bool renameFolders = (SendMessage(hCheckBox2, BM_GETCHECK, 0, 0) == BST_CHECKED);

            SaveCheckboxStates(isRecursive, renameFolders);

            std::wifstream file(GetTempDirectory() + L"FolderPath.txt");
            if (file.is_open()) {
                std::wstring folderPath;
                std::getline(file, folderPath);
                file.close();

                ProcessDirectory(folderPath, isRecursive, renameFolders, false);

                KillTimer(hWnd, DECODE_FLASH_TIMER_ID); // Ensure no conflicting timer

                encodeFlashCount = 0;
                SetTimer(hWnd, ENCODE_FLASH_TIMER_ID, 100, (TIMERPROC)FlashButtonProc);
                ShowWindow(GetDlgItem(hWnd, 5), SW_SHOW);
            }
            else {
                MessageBoxW(NULL, L"Folder path file not found.", L"Error", MB_OK | MB_ICONERROR);
            }
            break;
        }
        case 6: // ID for "Visit GitHub" button
            ShellExecute(NULL, L"open", L"https://github.com/s-vhs/AnimeOut-CommunityTools/tree/WinDecoder", NULL, NULL, SW_SHOWNORMAL);
            break;
        default:
            return DefWindowProc(hWnd, message, wParam, lParam);
        }
    }
    break;
    case WM_DESTROY:
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}
