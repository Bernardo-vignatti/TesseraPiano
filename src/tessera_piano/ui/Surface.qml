import QtQuick

Rectangle {
    radius: 14
    border.color: Theme.line
    gradient: Gradient {
        GradientStop { position: 0; color: Theme.surfaceTop }
        GradientStop { position: 1; color: Theme.surface }
    }
}
